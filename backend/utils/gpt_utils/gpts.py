import json
import time
import asyncio
from typing import Optional, Union, Dict, Any
from contextlib import asynccontextmanager
import sys

from openai import AsyncOpenAI, RateLimitError
import structlog
import tenacity

from prompts import transcript_prompts, slang_prompts
from schemas.gpt_schemas import ResponseSchema, SlangRequest, SlangsResponse, TranscriptRequest
from utils.gpt_utils.config import GPTConfig
from utils.gpt_utils.dataclasses import GPTMetrics
from utils.gpt_utils.exceptions import (
    APIQuotaError, 
    ContentFilterError, 
    GPTError, 
    ModelNotFoundError, 
    TokenLimitError, 
    ConfigurationError)

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

class GPT:
    """Production-ready GPT client with comprehensive error handling"""
    
    def __init__(self, config: Optional[GPTConfig] = None):
        self.config = config or GPTConfig()
        self.metrics = GPTMetrics()
        
        client_kwargs = {
            'api_key': self.config.api_key,
            'timeout': self.config.timeout,
            'max_retries': self.config.max_retries
        }
        
        if self.config.organization:
            client_kwargs['organization'] = self.config.organization
        
        self.client = AsyncOpenAI(**client_kwargs)
        
        logger.info("GPT client initialized", 
                   model=self.config.model,
                   timeout=self.config.timeout,
                   max_retries=self.config.max_retries)

    def _extract_usage_info(self, response: Any) -> Dict[str, int]:
        """Extract token usage information from response"""
        try:
            if hasattr(response, 'usage') and response.usage:
                return {
                    'prompt_tokens': response.usage.prompt_tokens or 0,
                    'completion_tokens': response.usage.completion_tokens or 0,
                    'total_tokens': response.usage.total_tokens or 0
                }
        except Exception as e:
            logger.warning("Could not extract usage info", error=str(e))
        
        return {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}

    def _handle_openai_error(self, error: Exception, operation: str) -> None:
        """Handle OpenAI-specific errors"""
        error_message = str(error).lower()
        
        if 'rate limit' in error_message:
            self.metrics.rate_limit_hits += 1
            raise RateLimitError(f"OpenAI rate limit exceeded during {operation}")
        elif 'quota' in error_message or 'insufficient_quota' in error_message:
            raise APIQuotaError(f"OpenAI API quota exceeded during {operation}")
        elif 'model' in error_message and 'not found' in error_message:
            raise ModelNotFoundError(f"Model {self.config.model} not found during {operation}")
        elif 'maximum context length' in error_message or 'token' in error_message:
            raise TokenLimitError(f"Token limit exceeded during {operation}")
        elif 'content_filter' in error_message or 'content policy' in error_message:
            raise ContentFilterError(f"Content filtered by OpenAI during {operation}")
        else:
            raise GPTError(f"OpenAI API error during {operation}: {error}")

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
        retry=tenacity.retry_if_exception_type((RateLimitError, GPTError)),
        reraise=True
    )
    async def _make_openai_request(
        self, 
        request_func,
        operation: str,
        request_id: str = None
    ):
        """Make OpenAI request with retry logic and error handling"""
        start_time = time.time()
        self.metrics.total_requests += 1
        
        try:
            logger.info("Making OpenAI request", 
                       operation=operation,
                       model=self.config.model,
                       request_id=request_id)
            
            response = await request_func()
            
            response_time = time.time() - start_time
            self.metrics.total_response_time += response_time
            self.metrics.successful_requests += 1
            
            usage_info = self._extract_usage_info(response)
            self.metrics.total_tokens_used += usage_info.get('total_tokens', 0)
            
            logger.info("OpenAI request successful",
                       operation=operation,
                       response_time=response_time,
                       tokens_used=usage_info.get('total_tokens', 0),
                       request_id=request_id)
            
            return response
            
        except Exception as e:
            self.metrics.failed_requests += 1
            logger.error("OpenAI request failed",
                        operation=operation,
                        error=str(e),
                        request_id=request_id)
            
            self._handle_openai_error(e, operation)

    async def generate_transcripts(
        self,
        request: Union[TranscriptRequest, dict],
        request_id: str = None
    ) -> Optional[ResponseSchema]:
        """Generate transcripts with comprehensive validation and error handling"""

        if isinstance(request, dict):
            try:
                request = TranscriptRequest(**request)
            except Exception as e:
                logger.error("Invalid transcript request", error=str(e), request_id=request_id)
                raise ValueError(f"Invalid request parameters: {e}")
        
        self.metrics.transcript_requests += 1
        
        try:
            async def make_request():
                return await self.client.responses.parse(
                    model=self.config.model,
                    instructions=transcript_prompts.system_prompt(
                        request.variations,
                        request.with_forecast,
                        request.forecast_days
                    ),
                    input=request.user_prompt,
                    text_format=ResponseSchema,
                    timeout=self.config.request_timeout
                )
            
            response = await self._make_openai_request(
                make_request, 
                "generate_transcripts",
                request_id
            )
            
            if response and hasattr(response, 'output_text'):
                logger.info("Transcripts generated successfully",
                           variations=request.variations,
                           with_forecast=request.with_forecast,
                           request_id=request_id)
                return response.output_parsed
            else:
                logger.warning("Empty response from OpenAI", request_id=request_id)
                return None
                
        except (RateLimitError, APIQuotaError, ModelNotFoundError, 
                TokenLimitError, ContentFilterError):
            # Re-raise specific errors
            raise
        except Exception as e:
            logger.error("Unexpected error generating transcripts",
                        error=str(e),
                        request_id=request_id)
            raise GPTError(f"Failed to generate transcripts: {e}")

    async def get_slangs(
        self,
        request: Union[SlangRequest, dict, str],
        request_id: str = None
    ) -> Optional[SlangsResponse]:
        """Get slangs with comprehensive validation and error handling"""
        
        if isinstance(request, str):
            request = SlangRequest(country=request)
        elif isinstance(request, dict):
            try:
                request = SlangRequest(**request)
            except Exception as e:
                logger.error("Invalid slang request", error=str(e), request_id=request_id)
                raise ValueError(f"Invalid request parameters: {e}")
        
        self.metrics.slang_requests += 1
        
        try:
            async def make_request():
                return await self.client.responses.parse(
                    model=self.config.model,
                    tools=[
                        {
                            "type": "web_search_preview"
                        }
                    ],
                    instructions=slang_prompts.system_prompt(),
                    input=json.dumps(slang_prompts.user_prompt(request.country)),
                    text_format=SlangsResponse,
                    timeout=self.config.request_timeout
                )
            
            response = await self._make_openai_request(
                make_request,
                "get_slangs", 
                request_id
            )
            
            if response and hasattr(response, 'output_text'):
                logger.info("Slangs retrieved successfully",
                           country=request.country,
                           request_id=request_id)
                return response.output_parsed
            else:
                logger.warning("Empty response from OpenAI", request_id=request_id)
                return None
                
        except (RateLimitError, APIQuotaError, ModelNotFoundError, 
                TokenLimitError, ContentFilterError):
            # Re-raise specific errors
            raise
        except Exception as e:
            logger.error("Unexpected error getting slangs",
                        country=request.country if hasattr(request, 'country') else 'unknown',
                        error=str(e),
                        request_id=request_id)
            raise GPTError(f"Failed to get slangs: {e}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get GPT usage metrics"""
        return {
            "total_requests": self.metrics.total_requests,
            "successful_requests": self.metrics.successful_requests,
            "failed_requests": self.metrics.failed_requests,
            "success_rate": self.metrics.success_rate,
            "average_response_time": self.metrics.average_response_time,
            "total_tokens_used": self.metrics.total_tokens_used,
            "average_tokens_per_request": self.metrics.average_tokens_per_request,
            "transcript_requests": self.metrics.transcript_requests,
            "slang_requests": self.metrics.slang_requests,
            "rate_limit_hits": self.metrics.rate_limit_hits,
            "uptime_seconds": time.time() - self.metrics.start_time
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        try:
            test_request = TranscriptRequest(
                user_prompt="Test health check prompt for API connectivity",
                with_forecast=False,
                variations=1
            )
            
            result = await self.generate_transcripts(test_request, request_id="health-check")
            
            return {
                "status": "healthy",
                "api_responsive": result is not None,
                "model": self.config.model,
                "timestamp": time.time()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "api_responsive": False,
                "error": str(e),
                "model": self.config.model,
                "timestamp": time.time()
            }

    async def close(self):
        """Clean up resources"""
        try:
            if hasattr(self.client, 'close'):
                await self.client.close()
            logger.info("GPT client closed successfully")
        except Exception as e:
            logger.error("Error closing GPT client", error=str(e))


@asynccontextmanager
async def create_gpt_client(config: GPTConfig = None):
    """Context manager for GPT client with proper resource management"""
    client = GPT(config=config)
    try:
        yield client
    except Exception as e:
        logger.error("Error in GPT context manager", error=str(e))
        raise
    finally:
        await client.close()