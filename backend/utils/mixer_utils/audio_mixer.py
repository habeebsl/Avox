import asyncio
import io
import time
from contextlib import asynccontextmanager
from typing import Dict, Optional, Any

from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError
from pydub.utils import which
import structlog

from utils.mixer_utils.exceptions import AudioFormatError, AudioProcessingError, ConfigurationError
from utils.mixer_utils.dataclasses import AudioFormat, AudioInfo, MixerConfig, MixerMetrics

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

class AudioMixer:
    """Production-ready audio mixer with comprehensive error handling"""
    
    def __init__(self, config: Optional[MixerConfig] = None):
        self.config = config or MixerConfig()
        self.metrics = MixerMetrics()
        
        # Check system dependencies
        self._validate_dependencies()
        
        logger.info("AudioMixer initialized", 
                   max_file_size_mb=self.config.max_file_size_mb,
                   supported_formats=list(self.config.supported_formats))
    
    def _validate_dependencies(self):
        """Validate required system dependencies"""
        if self.config.enable_ffmpeg_check:
            ffmpeg_path = which("ffmpeg")
            if not ffmpeg_path:
                logger.warning("FFmpeg not found - some audio formats may not work")
            else:
                logger.info("FFmpeg found", path=ffmpeg_path)
    
    def _validate_buffer(self, buffer: io.BytesIO, name: str) -> None:
        """Validate audio buffer"""
        if not isinstance(buffer, io.BytesIO):
            raise AudioFormatError(f"{name} must be a BytesIO object")
        
        current_pos = buffer.tell()
        buffer.seek(0, 2)  # Seek to end
        size = buffer.tell()
        buffer.seek(current_pos)  # Restore position
        
        if size == 0:
            raise AudioFormatError(f"{name} buffer is empty")
        
        max_size_bytes = self.config.max_file_size_mb * 1024 * 1024
        if size > max_size_bytes:
            raise AudioFormatError(
                f"{name} exceeds maximum size of {self.config.max_file_size_mb}MB "
                f"(actual: {size / 1024 / 1024:.1f}MB)"
            )
    
    def _validate_audio_format(self, format_str: str) -> AudioFormat:
        """Validate and normalize audio format"""
        if not format_str:
            raise AudioFormatError("Audio format cannot be empty")
        
        try:
            audio_format = AudioFormat(format_str.lower().strip())
        except ValueError:
            raise AudioFormatError(
                f"Unsupported audio format: {format_str}. "
                f"Supported formats: {[f.value for f in self.config.supported_formats]}"
            )
        
        if audio_format not in self.config.supported_formats:
            raise AudioFormatError(f"Audio format {audio_format.value} is not enabled")
        
        return audio_format
    
    def _load_audio_segment(self, buffer: io.BytesIO, format_str: str, name: str) -> AudioSegment:
        """Safely load audio segment from buffer"""
        try:
            buffer.seek(0)
            audio_format = self._validate_audio_format(format_str)
            
            # Try to load the audio
            audio = AudioSegment.from_file(buffer, format=audio_format.value)
            
            # Validate duration
            max_duration_ms = self.config.max_duration_minutes * 60 * 1000
            if len(audio) > max_duration_ms:
                raise AudioProcessingError(
                    f"{name} exceeds maximum duration of {self.config.max_duration_minutes} minutes "
                    f"(actual: {len(audio) / 1000 / 60:.1f} minutes)"
                )
            
            if audio.channels > 2:
                logger.warning(f"{name} has {audio.channels} channels, converting to stereo")
                audio = audio.set_channels(2)
            
            logger.debug("Audio loaded successfully",
                        name=name,
                        duration_ms=len(audio),
                        channels=audio.channels,
                        sample_rate=audio.frame_rate)
            
            return audio
            
        except CouldntDecodeError as e:
            raise AudioFormatError(f"Could not decode {name}: {e}")
        except Exception as e:
            raise AudioProcessingError(f"Failed to load {name}: {e}")
    
    def _get_audio_info(self, audio: AudioSegment, format_str: str) -> AudioInfo:
        """Get comprehensive audio information"""
        return AudioInfo(
            duration_ms=len(audio),
            duration_seconds=len(audio) / 1000.0,
            channels=audio.channels,
            sample_rate=audio.frame_rate,
            frame_rate=audio.frame_rate,
            format=format_str
        )
    
    async def get_audio_info(
        self, 
        audio_buffer: io.BytesIO, 
        format_str: str = "mp3",
        operation_id: str = None
    ) -> Optional[AudioInfo]:
        """Get audio information asynchronously"""
        start_time = time.time()
        self.metrics.total_operations += 1
        self.metrics.duration_operations += 1
        
        try:
            self._validate_buffer(audio_buffer, "audio")
            
            def _get_info_sync() -> AudioInfo:
                audio = self._load_audio_segment(audio_buffer, format_str, "audio")
                return self._get_audio_info(audio, format_str)
            
            logger.info("Getting audio info", format=format_str, operation_id=operation_id)
            
            info = await asyncio.to_thread(_get_info_sync)
            
            processing_time = time.time() - start_time
            self.metrics.total_processing_time += processing_time
            self.metrics.successful_operations += 1
            
            logger.info("Audio info retrieved successfully",
                       duration_seconds=info.duration_seconds,
                       channels=info.channels,
                       sample_rate=info.sample_rate,
                       processing_time=processing_time,
                       operation_id=operation_id)
            
            return info
            
        except (AudioFormatError, AudioProcessingError):
            self.metrics.failed_operations += 1
            raise
        except Exception as e:
            self.metrics.failed_operations += 1
            logger.error("Unexpected error getting audio info",
                        error=str(e),
                        operation_id=operation_id)
            raise AudioProcessingError(f"Failed to get audio info: {e}")
    
    async def get_audio_duration(
        self, 
        audio_buffer: io.BytesIO, 
        format_str: str = "mp3",
        operation_id: str = None
    ) -> Optional[int]:
        """Get audio duration in seconds (backward compatibility)"""
        try:
            info = await self.get_audio_info(audio_buffer, format_str, operation_id)
            return int(round(info.duration_seconds)) if info else None
        except Exception as e:
            logger.error("Error getting audio duration", error=str(e), operation_id=operation_id)
            return None
    
    async def merge_music_with_speech(
        self,
        speech_buffer: io.BytesIO,
        music_buffer: io.BytesIO,
        speech_format: str = "mp3",
        music_format: str = "mp3",
        output_format: str = "mp3",
        music_reduction_db: Optional[float] = None,
        fade_duration_ms: Optional[int] = None,
        music_extension_ms: Optional[int] = None,
        operation_id: str = None
    ) -> Optional[io.BytesIO]:
        """Merge music with speech with comprehensive configuration options"""
        start_time = time.time()
        self.metrics.total_operations += 1
        self.metrics.merge_operations += 1
        
        music_reduction_db = music_reduction_db or self.config.default_music_reduction_db
        fade_duration_ms = fade_duration_ms or self.config.default_fade_duration_ms
        music_extension_ms = music_extension_ms or self.config.music_extension_ms
        
        try:
            self._validate_buffer(speech_buffer, "speech")
            self._validate_buffer(music_buffer, "music")
            self._validate_audio_format(output_format)
            
            if music_reduction_db < 0:
                raise ValueError("music_reduction_db cannot be negative")
            if fade_duration_ms < 0:
                raise ValueError("fade_duration_ms cannot be negative")
            if music_extension_ms < 0:
                raise ValueError("music_extension_ms cannot be negative")
            
            def _merge_sync() -> io.BytesIO:
                speech = self._load_audio_segment(speech_buffer, speech_format, "speech")
                music = self._load_audio_segment(music_buffer, music_format, "music")
                
                logger.info("Audio loaded for merging",
                           speech_duration_ms=len(speech),
                           music_duration_ms=len(music),
                           operation_id=operation_id)
                
                speech_duration = len(speech)
                desired_music_duration = speech_duration + music_extension_ms
                
                if len(music) < desired_music_duration:
                    repetitions = (desired_music_duration // len(music)) + 1
                    logger.info("Extending music by repetition",
                               original_duration=len(music),
                               repetitions=repetitions,
                               operation_id=operation_id)
                    music = music * repetitions
                
                music = music[:desired_music_duration]
                
                music = music - music_reduction_db
                
                # Apply fade out to music
                actual_fade_duration = min(fade_duration_ms, len(music))
                if actual_fade_duration > 0:
                    music = music.fade_out(actual_fade_duration)
                    logger.debug("Applied fade out",
                                fade_duration_ms=actual_fade_duration,
                                operation_id=operation_id)
                
                # Overlay speech on music
                combined = music.overlay(speech, position=0)
                
                # Export to buffer
                buffer = io.BytesIO()
                combined.export(buffer, format=output_format)
                buffer.seek(0)
                
                logger.info("Audio merged successfully",
                           final_duration_ms=len(combined),
                           output_format=output_format,
                           operation_id=operation_id)
                
                return buffer
            
            logger.info("Starting audio merge",
                       speech_format=speech_format,
                       music_format=music_format,
                       output_format=output_format,
                       music_reduction_db=music_reduction_db,
                       operation_id=operation_id)
            
            result = await asyncio.to_thread(_merge_sync)
            
            processing_time = time.time() - start_time
            self.metrics.total_processing_time += processing_time
            self.metrics.successful_operations += 1
            
            logger.info("Audio merge completed successfully",
                       processing_time=processing_time,
                       operation_id=operation_id)
            
            return result
            
        except (AudioFormatError, AudioProcessingError, ValueError):
            self.metrics.failed_operations += 1
            raise
        except Exception as e:
            self.metrics.failed_operations += 1
            logger.error("Unexpected error in audio merge",
                        error=str(e),
                        operation_id=operation_id)
            raise AudioProcessingError(f"Failed to merge audio: {e}")
    
    async def convert_format(
        self,
        audio_buffer: io.BytesIO,
        input_format: str,
        output_format: str,
        operation_id: str = None
    ) -> Optional[io.BytesIO]:
        """Convert audio format"""
        start_time = time.time()
        self.metrics.total_operations += 1
        self.metrics.format_conversions += 1
        
        try:
            self._validate_buffer(audio_buffer, "audio")
            self._validate_audio_format(input_format)
            self._validate_audio_format(output_format)
            
            if input_format == output_format:
                logger.info("Input and output formats are the same, returning original",
                           format=input_format,
                           operation_id=operation_id)
                audio_buffer.seek(0)
                return audio_buffer
            
            def _convert_sync() -> io.BytesIO:
                audio = self._load_audio_segment(audio_buffer, input_format, "audio")
                
                buffer = io.BytesIO()
                audio.export(buffer, format=output_format)
                buffer.seek(0)
                
                return buffer
            
            logger.info("Converting audio format",
                       from_format=input_format,
                       to_format=output_format,
                       operation_id=operation_id)
            
            result = await asyncio.to_thread(_convert_sync)
            
            processing_time = time.time() - start_time
            self.metrics.total_processing_time += processing_time
            self.metrics.successful_operations += 1
            
            logger.info("Format conversion completed",
                       processing_time=processing_time,
                       operation_id=operation_id)
            
            return result
            
        except Exception as e:
            self.metrics.failed_operations += 1
            logger.error("Error converting audio format",
                        error=str(e),
                        operation_id=operation_id)
            raise AudioProcessingError(f"Failed to convert format: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get mixer performance metrics"""
        return {
            "total_operations": self.metrics.total_operations,
            "successful_operations": self.metrics.successful_operations,
            "failed_operations": self.metrics.failed_operations,
            "success_rate": self.metrics.success_rate,
            "average_processing_time": self.metrics.average_processing_time,
            "uptime_seconds": time.time() - self.metrics.start_time,
            "operation_breakdown": {
                "merge_operations": self.metrics.merge_operations,
                "duration_operations": self.metrics.duration_operations,
                "format_conversions": self.metrics.format_conversions
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check by testing basic functionality"""
        try:
            test_audio = AudioSegment.silent(duration=1000)  # 1 second
            test_buffer = io.BytesIO()
            test_audio.export(test_buffer, format="mp3")
            test_buffer.seek(0)
            
            info = await self.get_audio_info(test_buffer, "mp3", "health_check")
            
            return {
                "status": "healthy",
                "mixer_functional": info is not None,
                "test_duration_seconds": info.duration_seconds if info else None,
                "timestamp": time.time()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "mixer_functional": False,
                "error": str(e),
                "timestamp": time.time()
            }


@asynccontextmanager
async def create_audio_mixer(config: MixerConfig = None):
    """Context manager for AudioMixer"""
    mixer = AudioMixer(config=config)
    try:
        yield mixer
    except Exception as e:
        logger.error("Error in AudioMixer context manager", error=str(e))
        raise