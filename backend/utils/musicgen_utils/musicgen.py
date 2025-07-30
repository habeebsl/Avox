import io
from typing import Optional, Dict, Any, Union
import time

import httpx
import replicate
from replicate.helpers import FileOutput
from dotenv import load_dotenv
import tenacity
import structlog

from utils.musicgen_utils.config import MusicGenConfig
from utils.musicgen_utils.dataclasses import ModelVersion, MusicGenMetrics, OutputFormat
from utils.musicgen_utils.exceptions import DownloadError, GenerationError

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


class MusicGen:
    """Production-ready MusicGen client"""

    def __init__(self, config: Optional[MusicGenConfig] = None):
        self.config = config or MusicGenConfig()
        self.model_id = "meta/musicgen:671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb"
        self.metrics = MusicGenMetrics()
        
        if self.config.replicate_token:
            replicate.Client(api_token=self.config.replicate_token)
        
        logger.info("MusicGen initialized", 
                   model=self.config.default_model.value,
                   max_duration=self.config.max_duration)

    def _validate_prompt(self, prompt: str) -> str:
        """Validate and sanitize prompt"""
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        
        prompt = prompt.strip()
        
        if len(prompt) < 3:
            raise ValueError("Prompt must be at least 3 characters long")
        
        return prompt

    def _validate_duration(self, duration: int) -> int:
        """Validate duration parameter"""
        if not isinstance(duration, int):
            raise ValueError("Duration must be an integer")
        
        if duration < self.config.min_duration:
            logger.warning("Duration too short, setting to minimum", 
                          requested=duration, minimum=self.config.min_duration)
            return self.config.min_duration
        
        if duration > self.config.max_duration:
            logger.warning("Duration too long, setting to maximum",
                          requested=duration, maximum=self.config.max_duration)
            return self.config.max_duration
        
        return duration

    def _build_generation_params(
        self, 
        prompt: str, 
        duration: int,
        model_version: Optional[ModelVersion] = None,
        output_format: Optional[OutputFormat] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Build parameters for music generation"""
        
        model_version = model_version or self.config.default_model
        output_format = output_format or self.config.default_format
        
        params = {
            "prompt": prompt,
            "duration": duration,
            "model_version": model_version.value,
            "output_format": output_format.value,
            "normalization_strategy": self.config.default_normalization.value,
            
            "top_k": kwargs.get("top_k", 250),
            "top_p": kwargs.get("top_p", 0),
            "temperature": kwargs.get("temperature", 1.0),
            "classifier_free_guidance": kwargs.get("classifier_free_guidance", 3),
            "continuation": kwargs.get("continuation", False),
            "continuation_start": kwargs.get("continuation_start", 0),
            "multi_band_diffusion": kwargs.get("multi_band_diffusion", False),
        }
        
        if not (0.0 <= params["temperature"] <= 2.0):
            logger.warning("Temperature out of range, clamping", 
                          temperature=params["temperature"])
            params["temperature"] = max(0.0, min(2.0, params["temperature"]))
        
        if not (1 <= params["classifier_free_guidance"] <= 10):
            logger.warning("CFG out of range, clamping", 
                          cfg=params["classifier_free_guidance"])
            params["classifier_free_guidance"] = max(1, min(10, params["classifier_free_guidance"]))
        
        return params

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(2),  # Only retry once for expensive operations
        wait=tenacity.wait_exponential(multiplier=2, min=5, max=30),
        retry=tenacity.retry_if_exception_type((replicate.exceptions.ReplicateError, Exception)),
        reraise=True
    )
    async def _generate_music(self, params: Dict[str, Any], request_id: str = None) -> str:
        """Generate music using Replicate API with retry logic"""
        logger.info("Starting music generation", 
                   prompt=params["prompt"][:50] + "..." if len(params["prompt"]) > 50 else params["prompt"],
                   duration=params["duration"],
                   model=params["model_version"],
                   request_id=request_id)
        
        try:
            output = await replicate.async_run(self.model_id, input=params)
            
            if not output:
                raise GenerationError("Replicate returned empty output")
            
            if isinstance(output, list) and len(output) > 0:
                output = output[0]  # Take first result if list
            
            if isinstance(output, FileOutput):
                output = output.url
            
            if not isinstance(output, str):
                raise GenerationError(f"Unexpected output type: {type(output)}")
            
            logger.info("Music generation completed", 
                       output_url=output[:100] + "..." if len(output) > 100 else output,
                       request_id=request_id)
            
            return output
            
        except replicate.exceptions.ReplicateError as e:
            logger.error("Replicate API error", error=str(e), request_id=request_id)
            raise GenerationError(f"Replicate API error: {e}")
        except Exception as e:
            logger.error("Unexpected generation error", error=str(e), request_id=request_id)
            raise GenerationError(f"Music generation failed: {e}")

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
        retry=tenacity.retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
        reraise=True
    )
    async def _download_audio(self, url: str, request_id: str = None) -> io.BytesIO:
        """Download generated audio with retry logic"""
        logger.info("Downloading generated audio", url=url[:100] + "...", request_id=request_id)
        
        try:
            async with httpx.AsyncClient(timeout=self.config.download_timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                content_type = response.headers.get("content-type", "")
                if not content_type.startswith(("audio/", "application/octet-stream")):
                    logger.warning("Unexpected content type", 
                                 content_type=content_type, 
                                 request_id=request_id)
                
                content_length = len(response.content)
                if content_length == 0:
                    raise DownloadError("Downloaded file is empty")
                
                if content_length < 1000:  # Less than 1KB is suspicious
                    logger.warning("Downloaded file is very small", 
                                 size_bytes=content_length, 
                                 request_id=request_id)
                
                audio_buffer = io.BytesIO(response.content)
                audio_buffer.seek(0)
                
                logger.info("Audio download completed", 
                           size_bytes=content_length,
                           request_id=request_id)
                
                return audio_buffer
                
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error downloading audio", 
                        status_code=e.response.status_code,
                        url=url,
                        request_id=request_id)
            raise DownloadError(f"HTTP {e.response.status_code}: Failed to download audio")
        except httpx.TimeoutException as e:
            logger.error("Timeout downloading audio", error=str(e), request_id=request_id)
            raise DownloadError(f"Download timeout: {e}")
        except httpx.RequestError as e:
            logger.error("Request error downloading audio", error=str(e), request_id=request_id)
            raise DownloadError(f"Download failed: {e}")
        except Exception as e:
            logger.error("Unexpected download error", error=str(e), request_id=request_id)
            raise DownloadError(f"Unexpected download error: {e}")

    async def generate_background_music(
        self, 
        prompt: str, 
        duration: int = 20,
        model_version: Optional[Union[ModelVersion, str]] = None,
        output_format: Optional[Union[OutputFormat, str]] = None,
        request_id: str = None,
        **generation_params
    ) -> Optional[io.BytesIO]:
        """
        Generate background music with comprehensive error handling
        
        Args:
            prompt: Text description of the desired music
            duration: Length in seconds (5-120)
            model_version: MusicGen model to use
            output_format: Audio format (mp3/wav)
            request_id: Optional request ID for tracking
            **generation_params: Additional generation parameters
        
        Returns:
            BytesIO buffer containing the generated audio, or None if failed
        """
        start_time = time.time()
        self.metrics.total_generations += 1
        
        try:
            prompt = self._validate_prompt(prompt)
            duration = self._validate_duration(duration)
            
            if isinstance(model_version, str):
                model_version = ModelVersion(model_version.lower())
            if isinstance(output_format, str):
                output_format = OutputFormat(output_format.lower())
            
            params = self._build_generation_params(
                prompt=prompt,
                duration=duration,
                model_version=model_version,
                output_format=output_format,
                **generation_params
            )
            
            generation_start = time.time()
            output_url = await self._generate_music(params, request_id)
            generation_time = time.time() - generation_start
            self.metrics.total_generation_time += generation_time
            
            download_start = time.time()
            audio_buffer = await self._download_audio(output_url, request_id)
            download_time = time.time() - download_start
            self.metrics.total_download_time += download_time
            
            self.metrics.successful_generations += 1
            total_time = time.time() - start_time
            
            logger.info("Music generation successful",
                       prompt=prompt[:50] + "..." if len(prompt) > 50 else prompt,
                       duration=duration,
                       generation_time=generation_time,
                       download_time=download_time,
                       total_time=total_time,
                       audio_size=len(audio_buffer.getvalue()),
                       request_id=request_id)
            
            return audio_buffer
            
        except (ValueError, TypeError) as e:
            self.metrics.failed_generations += 1
            logger.error("Invalid parameters for music generation",
                        error=str(e),
                        prompt=prompt[:100] if 'prompt' in locals() else None,
                        duration=duration if 'duration' in locals() else None,
                        request_id=request_id)
            return None
            
        except (GenerationError, DownloadError) as e:
            self.metrics.failed_generations += 1
            logger.error("Music generation failed",
                        error=str(e),
                        prompt=prompt[:100] if 'prompt' in locals() else None,
                        request_id=request_id)
            return None
            
        except Exception as e:
            self.metrics.failed_generations += 1
            logger.error("Unexpected error in music generation",
                        error=str(e),
                        error_type=type(e).__name__,
                        prompt=prompt[:100] if 'prompt' in locals() else None,
                        request_id=request_id)
            return None

    def get_metrics(self) -> Dict[str, Any]:
        """Get generation metrics"""
        return {
            "total_generations": self.metrics.total_generations,
            "successful_generations": self.metrics.successful_generations,
            "failed_generations": self.metrics.failed_generations,
            "success_rate": self.metrics.success_rate,
            "average_generation_time": self.metrics.average_generation_time,
            "total_generation_time": self.metrics.total_generation_time,
            "total_download_time": self.metrics.total_download_time,
            "uptime_seconds": time.time() - self.metrics.start_time
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check with a quick generation test"""
        try:
            test_prompt = "simple piano melody"
            result = await self.generate_background_music(
                prompt=test_prompt,
                duration=self.config.min_duration,
                request_id="health-check"
            )
            
            return {
                "status": "healthy" if result is not None else "degraded",
                "api_responsive": result is not None,
                "test_prompt": test_prompt,
                "timestamp": time.time()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "api_responsive": False,
                "error": str(e),
                "timestamp": time.time()
            }