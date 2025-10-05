import asyncio
import io
import json
import os
import uuid
import time
from contextlib import asynccontextmanager
from typing import Dict, List, Literal, Optional, Any, Union
import sys

from dotenv import load_dotenv
from elevenlabs import AddVoiceIvcResponseModel, ForcedAlignmentResponseModel, Voice
from elevenlabs.client import AsyncElevenLabs
from elevenlabs.core import ApiError
import structlog

from schemas.speech_generator_schemas import SpeechRequest, VoiceData
from schemas.ws_schemas import AudioBuffer
from utils.speech_generator_utils.config import SpeechGeneratorConfig
from utils.speech_generator_utils.dataclasses import OutputFormat, SpeechMetrics, VoiceType
from utils.speech_generator_utils.exceptions import (
    InvalidAudioError, 
    QuotaExceededError, 
    SpeechGeneratorError, 
    TextTooLongError, 
    VoiceNotFoundError,
    ConfigurationError)

load_dotenv()

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class SpeechGenerator:
    """Production-ready Speech Generator client"""
    
    def __init__(self, config: Optional[SpeechGeneratorConfig] = None):
        self.config = config or SpeechGeneratorConfig()
        self.metrics = SpeechMetrics()
        self._client: Optional[AsyncElevenLabs] = None
        
        logger.info("SpeechGenerator initialized", 
                   model=self.config.model,
                   output_format=self.config.default_output_format.value)

    async def __aenter__(self):
        """Initialize the ElevenLabs client"""
        if self._client is None:
            self._client = AsyncElevenLabs(
                api_key=self.config.api_key,
                timeout=self.config.request_timeout
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up client resources"""
        if self._client:
            self._client = None

    def _get_client(self) -> AsyncElevenLabs:
        """Get the ElevenLabs client, ensuring it's initialized"""
        if not self._client:
            raise SpeechGeneratorError("Client not initialized. Use async context manager.")
        return self._client

    def _handle_elevenlabs_error(self, error: Exception, operation: str) -> None:
        """Handle ElevenLabs API errors with specific exceptions"""
        if isinstance(error, ApiError):
            status_code = getattr(error, 'status_code', None)
            error_message = str(error)
            
            if status_code == 401:
                raise ConfigurationError(f"Invalid API key: {error_message}")
            elif status_code == 403:
                raise QuotaExceededError(f"API quota exceeded: {error_message}")
            elif status_code == 404:
                raise VoiceNotFoundError(f"Voice not found: {error_message}")
            elif status_code == 422:
                if "text" in error_message.lower():
                    raise TextTooLongError(f"Text too long or invalid: {error_message}")
                else:
                    raise InvalidAudioError(f"Invalid audio data: {error_message}")
            else:
                raise SpeechGeneratorError(f"ElevenLabs API error in {operation}: {error_message}")
        else:
            raise SpeechGeneratorError(f"Unexpected error in {operation}: {error}")

    def format_voice_data(self, voice: Voice) -> VoiceData:
        """Format voice data with comprehensive error handling"""
        try:
            name = getattr(voice, 'name', None) or 'Unknown'
            voice_id = getattr(voice, 'voice_id', None) or ''
            description = getattr(voice, 'description', None)
            labels = getattr(voice, 'labels', None)
            category = getattr(voice, 'category', None)
            
            if labels and not isinstance(labels, dict):
                try:
                    labels = dict(labels) if hasattr(labels, '__iter__') else None
                except (TypeError, ValueError):
                    labels = None
            
            return VoiceData(
                voice_name=name,
                voice_id=voice_id,
                description=description,
                labels=labels,
                category=category
            )
            
        except Exception as e:
            logger.warning("Error formatting voice data", 
                          voice_id=getattr(voice, 'voice_id', 'unknown'),
                          error=str(e))
            
            return VoiceData(
                voice_name=getattr(voice, 'name', 'Unknown'),
                voice_id=getattr(voice, 'voice_id', str(uuid.uuid4())),
                description="Data formatting error"
            )

    async def generate_speech(
        self, 
        request: Union[SpeechRequest, dict, str],
        output_format: Optional[OutputFormat] = None,
        request_id: Optional[str] = None
    ) -> Optional[io.BytesIO]:
        """Generate speech with comprehensive error handling and validation"""
        start_time = time.time()
        self.metrics.total_generations += 1
        
        try:
            if isinstance(request, str):
                speech_request = SpeechRequest(
                    text=request,
                    voice_id=os.getenv('ELEVENLABS_DEFAULT_VOICE_ID', 'pNInz6obpgDQGcFmaJgB')
                )
            elif isinstance(request, dict):
                speech_request = SpeechRequest(**request)
            elif isinstance(request, SpeechRequest):
                speech_request = request
            else:
                raise ValueError("Invalid request format")
            
            output_format = output_format or self.config.default_output_format
            
            logger.info("Generating speech", 
                       text_length=len(speech_request.text),
                       voice_id=speech_request.voice_id,
                       speed=speech_request.speed,
                       output_format=output_format.value,
                       request_id=request_id)
            
            client = self._get_client()
            
            voice_settings = {"speed": speech_request.speed}
            if speech_request.stability is not None:
                voice_settings["stability"] = speech_request.stability
            if speech_request.similarity_boost is not None:
                voice_settings["similarity_boost"] = speech_request.similarity_boost
            if speech_request.style is not None:
                voice_settings["style"] = speech_request.style
            
            audio_stream = client.text_to_speech.convert(
                text=speech_request.text,
                voice_id=speech_request.voice_id,
                model_id=self.config.model,
                output_format=output_format.value,
                voice_settings=voice_settings,
            )

            audio_chunks = []
            chunk_count = 0
            
            async for chunk in audio_stream:
                audio_chunks.append(chunk)
                chunk_count += 1
                    
                if chunk_count > 10000:
                    logger.warning("Too many audio chunks, possible streaming issue")
                    break
            
            if not audio_chunks:
                logger.error("No audio data received", request_id=request_id)
                self.metrics.failed_generations += 1
                return None
            
            audio_bytes = b"".join(audio_chunks)
            
            if len(audio_bytes) == 0:
                logger.error("Empty audio data", request_id=request_id)
                self.metrics.failed_generations += 1
                return None
            
            audio_io = io.BytesIO(audio_bytes)
            audio_io.seek(0)
            
            generation_time = time.time() - start_time
            self.metrics.successful_generations += 1
            self.metrics.total_generation_time += generation_time
            
            logger.info("Speech generation successful",
                       audio_size_bytes=len(audio_bytes),
                       generation_time=generation_time,
                       chunks=len(audio_chunks),
                       request_id=request_id)
            
            return audio_io
            
        except Exception as e:
            self.metrics.failed_generations += 1
            generation_time = time.time() - start_time
            
            logger.error("Speech generation failed",
                        error=str(e),
                        generation_time=generation_time,
                        request_id=request_id)
            
            self._handle_elevenlabs_error(e, "generate_speech")
            return None

    async def get_voices(
        self, 
        query: str = "",
        voice_type: VoiceType = VoiceType.NON_DEFAULT,
        limit: int = 100,
        request_id: Optional[str] = None
    ) -> List[VoiceData]:
        """Get voices with enhanced search and error handling"""
        try:
            logger.info("Fetching voices", 
                       query=query,
                       voice_type=voice_type.value,
                       limit=limit,
                       request_id=request_id)
            
            client = self._get_client()
            
            # Use search if query provided, otherwise get all voices
            if query.strip():
                data = await client.voices.search(
                    search=query.strip(),
                    voice_type=voice_type.value
                )
                voices_list = getattr(data, 'voices', [])
            else:
                data = await client.voices.get_all()
                voices_list = getattr(data, 'voices', [])
            
            if not voices_list:
                logger.warning("No voices found", 
                              query=query,
                              voice_type=voice_type.value,
                              request_id=request_id)
                return []
            
            formatted_voices = []
            for voice in voices_list[:limit]:  # Respect limit
                try:
                    formatted = self.format_voice_data(voice)
                    formatted_voices.append(formatted)
                except Exception as e:
                    logger.warning("Failed to format voice",
                                  voice_id=getattr(voice, 'voice_id', 'unknown'),
                                  error=str(e),
                                  request_id=request_id)
                    continue
            
            self.metrics.voices_fetched += len(formatted_voices)
            
            logger.info("Voices retrieved successfully",
                       count=len(formatted_voices),
                       request_id=request_id)
            
            return formatted_voices
            
        except Exception as e:
            logger.error("Error getting voices",
                        query=query,
                        error=str(e),
                        request_id=request_id)
            
            self._handle_elevenlabs_error(e, "get_voices")
            return []

    async def get_voice(
        self, 
        voice_id: str,
        request_id: Optional[str] = None
    ) -> Optional[VoiceData]:
        """Get a single voice with error handling"""
        try:
            if not voice_id or not voice_id.strip():
                raise ValueError("Voice ID cannot be empty")
            
            voice_id = voice_id.strip()
            
            logger.info("Fetching voice", voice_id=voice_id, request_id=request_id)
            
            client = self._get_client()
            voice_data = await client.voices.get(voice_id=voice_id)
            
            formatted = self.format_voice_data(voice_data)
            
            logger.info("Voice retrieved successfully", 
                       voice_id=voice_id,
                       voice_name=formatted.voice_name,
                       request_id=request_id)
            
            return formatted
            
        except Exception as e:
            logger.error("Error getting voice",
                        voice_id=voice_id,
                        error=str(e),
                        request_id=request_id)
            
            self._handle_elevenlabs_error(e, "get_voice")
            return None

    async def get_forced_alignment(
        self, 
        transcript: str, 
        audio_buffer: io.BytesIO,
        request_id: Optional[str] = None
    ) -> Optional[ForcedAlignmentResponseModel]:
        """Get forced alignment with enhanced error handling"""
        try:
            if not transcript or not transcript.strip():
                raise ValueError("Transcript cannot be empty")
            
            if not audio_buffer:
                raise ValueError("Audio buffer cannot be None")
            
            current_pos = audio_buffer.tell()
            audio_buffer.seek(0, 2)
            audio_size = audio_buffer.tell()
            audio_buffer.seek(current_pos)
            
            if audio_size == 0:
                raise InvalidAudioError("Audio buffer is empty")
            
            if audio_size > 25 * 1024 * 1024:
                raise InvalidAudioError("Audio file too large (max 25MB)")
            
            transcript = transcript.strip()
            
            logger.info("Processing forced alignment",
                       transcript_length=len(transcript),
                       audio_size_bytes=audio_size,
                       request_id=request_id)
            
            client = self._get_client()
            
            data = await client.forced_alignment.create(
                text=transcript,
                file=audio_buffer
            )
            
            self.metrics.forced_alignments_processed += 1
            
            logger.info("Forced alignment successful",
                       words_count=len(getattr(data, 'words', [])),
                       request_id=request_id)
            
            return data
            
        except Exception as e:
            logger.error("Error in forced alignment",
                        transcript_length=len(transcript) if transcript else 0,
                        error=str(e),
                        request_id=request_id)
            
            self._handle_elevenlabs_error(e, "get_forced_alignment")
            return None

    async def generate_music(self, prompt: str, duration: int | float, request_id: Optional[str] = None):
        """Generate music with enhanced error handling"""
        start_time = time.time()
        self.metrics.total_generations += 1
        
        try:
            # Convert Duration to milliseconds
            duration_ms = int(duration * 1000)

            # Add instrumental specification to prompt
            instrumental_prompt = f"{prompt}. Instrumental only, no singing or vocals, pure background music without any human voice."

            logger.info("Generating music",
                       original_prompt=prompt,
                       enhanced_prompt=instrumental_prompt,
                       duration_seconds=duration,
                       duration_ms=duration_ms,
                       request_id=request_id)

            client: AsyncElevenLabs = self._get_client()
            music_stream = client.music.compose(
                prompt=instrumental_prompt,
                music_length_ms=duration_ms
            )

            audio_chunks = []
            chunk_count = 0
            
            async for chunk in music_stream:
                audio_chunks.append(chunk)
                chunk_count += 1
                    
                if chunk_count > 10000:
                    logger.warning("Too many audio chunks, possible streaming issue")
                    break
            
            if not audio_chunks:
                logger.error("No audio data received", request_id=request_id)
                self.metrics.failed_generations += 1
                return None
            
            audio_bytes = b"".join(audio_chunks)
            
            if len(audio_bytes) == 0:
                logger.error("Empty audio data", request_id=request_id)
                self.metrics.failed_generations += 1
                return None
            
            audio_io = io.BytesIO(audio_bytes)
            audio_io.seek(0)
            
            generation_time = time.time() - start_time
            self.metrics.successful_generations += 1
            self.metrics.total_generation_time += generation_time
            
            logger.info("Music generation successful",
                       audio_size_bytes=len(audio_bytes),
                       generation_time=generation_time,
                       chunks=len(audio_chunks),
                       request_id=request_id)
            
            return audio_io
            
        except Exception as e:
            self.metrics.failed_generations += 1
            generation_time = time.time() - start_time
            
            logger.error("Music generation failed",
                        error=str(e),
                        error_type=type(e).__name__,
                        generation_time=generation_time,
                        request_id=request_id,
                        exc_info=True)
            
            self._handle_elevenlabs_error(e, "generate_music")
            return None


    async def clone_voice(
        self, 
        files: List[AudioBuffer], 
        name: Optional[str] = None,
        description: Optional[str] = None,
        remove_background_noise: bool = True,
        request_id: Optional[str] = None,
        langauge_code: str = 'en'
    ) -> Optional[AddVoiceIvcResponseModel]:
        """Clone voice with enhanced validation and error handling"""
        try:
            if not files or len(files) == 0:
                raise ValueError("At least one audio file is required for voice cloning")
            
            if len(files) > 12:  # ElevenLabs limit
                raise ValueError("Too many files (max 12 for voice cloning)")
            
            if not name:
                name = f'Cloned-{uuid.uuid4().hex[:8]}'
            else:
                name = name.strip()
                if len(name) > 100:
                    name = name[:100]
            
            logger.info("Cloning voice",
                       file_count=len(files),
                       voice_name=name,
                       remove_noise=remove_background_noise,
                       request_id=request_id)
            
            client = self._get_client()
            
            data = await client.voices.ivc.create(
                name=name,
                files=files,
                description=description,
                remove_background_noise=remove_background_noise,
                labels=json.dumps({ 'language': langauge_code })
            )
            
            self.metrics.voice_clones_created += 1
            
            logger.info("Voice cloning successful",
                       voice_id=getattr(data, 'voice_id', 'unknown'),
                       voice_name=name,
                       request_id=request_id)
            
            return data
            
        except Exception as e:
            logger.error("Error cloning voice",
                        file_count=len(files) if files else 0,
                        voice_name=name,
                        error=str(e),
                        request_id=request_id)
            
            self._handle_elevenlabs_error(e, "clone_voice")
            return None

    async def delete_voice(
        self, 
        voice_id: str,
        request_id: Optional[str] = None
    ) -> bool:
        """Delete voice with error handling"""
        try:
            if not voice_id or not voice_id.strip():
                raise ValueError("Voice ID cannot be empty")
            
            voice_id = voice_id.strip()
            
            logger.info("Deleting voice", voice_id=voice_id, request_id=request_id)
            
            client = self._get_client()
            response = await client.voices.delete(voice_id=voice_id)
            
            success = getattr(response, 'status', None) == 'ok'
            
            if success:
                logger.info("Voice deleted successfully", 
                           voice_id=voice_id,
                           request_id=request_id)
            else:
                logger.warning("Voice deletion may have failed",
                              voice_id=voice_id,
                              response_status=getattr(response, 'status', None),
                              request_id=request_id)
            
            return success
            
        except Exception as e:
            logger.error("Error deleting voice",
                        voice_id=voice_id,
                        error=str(e),
                        request_id=request_id)
            
            self._handle_elevenlabs_error(e, "delete_voice")
            return False

    def get_metrics(self) -> Dict[str, Any]:
        """Get speech generation metrics"""
        return {
            "total_generations": self.metrics.total_generations,
            "successful_generations": self.metrics.successful_generations,
            "failed_generations": self.metrics.failed_generations,
            "success_rate": self.metrics.success_rate,
            "average_generation_time": self.metrics.average_generation_time,
            "voices_fetched": self.metrics.voices_fetched,
            "voice_clones_created": self.metrics.voice_clones_created,
            "forced_alignments_processed": self.metrics.forced_alignments_processed,
            "uptime_seconds": time.time() - self.metrics.start_time
        }

    async def health_check(self, test_voice_id: str = None) -> Dict[str, Any]:
        """Perform health check"""
        try:
            voices = await self.get_voices(limit=1)
            
            voice_check = True
            if test_voice_id:
                voice_data = await self.get_voice(test_voice_id)
                voice_check = voice_data is not None
            
            return {
                "status": "healthy",
                "api_responsive": len(voices) > 0,
                "voice_check_passed": voice_check,
                "available_voices": len(voices),
                "timestamp": time.time()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "api_responsive": False,
                "error": str(e),
                "timestamp": time.time()
            }


@asynccontextmanager
async def create_speech_generator(config: SpeechGeneratorConfig = None):
    """Context manager for SpeechGenerator with proper resource management"""
    generator = SpeechGenerator(config=config)
    try:
        async with generator:
            yield generator
    except Exception as e:
        logger.error("Error in SpeechGenerator context manager", error=str(e))
        raise