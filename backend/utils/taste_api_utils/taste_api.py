import asyncio
import os
import sys
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Tuple, Any, Union
import time

import httpx
from dotenv import load_dotenv
import tenacity
from aiolimiter import AsyncLimiter
import structlog

from schemas.taste_schemas import InsightsResponse, RecommendationItem
from utils.taste_api_utils.config import TasteAPIConfig
from utils.taste_api_utils.dataclasses import APIMetrics, FilterType
from utils.taste_api_utils.exceptions import RateLimitError, TasteAPIError, ConfigurationError, APIError

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

class TasteAPI:
    """Production-ready TasteAPI client"""
    
    def __init__(self, location: Optional[str] = None, config: Optional[TasteAPIConfig] = None):
        self.config = config or TasteAPIConfig()
        self.location = location or os.getenv('DEFAULT_LOCATION', 'Nigeria')
        self.metrics = APIMetrics()
        self._client: Optional[httpx.AsyncClient] = None
        self._limiter = AsyncLimiter(
            max_rate=self.config.max_rate, 
            time_period=self.config.time_period
        )
        
        if not self.location or len(self.location.strip()) < 2:
            raise ConfigurationError("Valid location is required")
        
        logger.info("TasteAPI initialized", location=self.location)

    async def __aenter__(self):
        """Create shared HTTP client when entering context"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
                headers={"User-Agent": f"TasteAPI-Client/1.0"}
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Properly close HTTP client when exiting context"""
        if self._client:
            await self._client.aclose()
            self._client = None

    def get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for requests"""
        return {
            "accept": "application/json",
            "X-Api-Key": self.config.api_key,
            "User-Agent": "TasteAPI-Client/1.0"
        }

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
        retry=tenacity.retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
        reraise=True
    )
    async def _make_request(self, url: str, request_id: str = None) -> httpx.Response:
        """Make HTTP request with comprehensive error handling"""
        start_time = time.time()
        self.metrics.total_requests += 1
        
        if not self._client:
            raise TasteAPIError("HTTP client not initialized. Use async context manager.")
        
        try:
            logger.info("Making API request", url=url, request_id=request_id)
            
            response = await self._client.get(
                url,
                headers=self.get_headers(),
                timeout=self.config.timeout
            )
            
            response_time = time.time() - start_time
            self.metrics.total_response_time += response_time
            
            if response.status_code == 200:
                self.metrics.successful_requests += 1
                logger.info("Request successful", 
                          status_code=response.status_code,
                          response_time=response_time,
                          request_id=request_id)
                return response
            elif response.status_code == 429:
                self.metrics.failed_requests += 1
                logger.warning("Rate limit exceeded", request_id=request_id)
                raise RateLimitError("API rate limit exceeded")
            elif response.status_code >= 500:
                self.metrics.failed_requests += 1
                logger.error("Server error", 
                           status_code=response.status_code,
                           request_id=request_id)
                raise APIError(f"Server error: {response.status_code}", response.status_code)
            else:
                self.metrics.failed_requests += 1
                logger.error("API error",
                           status_code=response.status_code,
                           response_text=response.text[:200],
                           request_id=request_id)
                raise APIError(
                    f"API error: {response.status_code}", 
                    response.status_code, 
                    response.json() if response.headers.get("content-type") == "application/json" else None
                )
                
        except httpx.TimeoutException as e:
            self.metrics.failed_requests += 1
            logger.error("Request timeout", error=str(e), request_id=request_id)
            raise APIError(f"Request timeout: {e}")
        except httpx.RequestError as e:
            self.metrics.failed_requests += 1
            logger.error("Request error", error=str(e), request_id=request_id)
            raise APIError(f"Request error: {e}")

    def _parse_recommendations(self, data: Dict[str, Any], filter_type: str) -> List[RecommendationItem]:
        """Parse and validate recommendation data"""
        recommendations = []
        
        entities = data.get('results', {}).get('entities', [])
        if not isinstance(entities, list):
            logger.warning("Invalid entities format", filter_type=filter_type)
            return recommendations
        
        for item in entities:
            if not isinstance(item, dict):
                continue
                
            try:
                name = item.get('name', '').strip()
                if not name:
                    continue
                
                tags = []
                if 'tags' in item and isinstance(item['tags'], list):
                    tags = [
                        tag.get('name', '').strip() 
                        for tag in item['tags'][:self.config.max_tags]
                        if isinstance(tag, dict) and tag.get('name', '').strip()
                    ]
                
                popularity = item.get('popularity')
                if popularity is not None:
                    try:
                        popularity = float(popularity)
                        if not (0.0 <= popularity <= 1.0):
                            popularity = None
                    except (ValueError, TypeError):
                        popularity = None
                
                recommendation = RecommendationItem(
                    name=name,
                    tags=tags,
                    popularity=popularity
                )
                
                recommendations.append(recommendation)
                
                if len(recommendations) >= self.config.max_recommendations:
                    break
                    
            except Exception as e:
                logger.warning("Failed to parse recommendation item", 
                             error=str(e), item=item, filter_type=filter_type)
                continue
        
        return recommendations

    async def get_insights(
        self, 
        filter_type: Union[FilterType, str],
        request_id: Optional[str] = None
    ) -> Optional[InsightsResponse]:
        """Get insights for a specific filter type with comprehensive error handling"""
        
        if isinstance(filter_type, str):
            try:
                filter_type = FilterType(filter_type.lower())
            except ValueError:
                logger.error("Invalid filter type", filter_type=filter_type)
                raise ValueError(f"Invalid filter type: {filter_type}")

        async with self._limiter:
            insights_url = (
                f"{self.config.base_url}/v2/insights?"
                f"filter.type=urn:entity:{filter_type.value}"
                f"&feature.explainability=true"
                f"&filter.location.query={self.location}"
                f"&sort_by=affinity"
            )
            
            try:
                response = await self._make_request(insights_url, request_id)
                data = response.json()
                
                recommendations = self._parse_recommendations(data, filter_type.value)
                
                result = InsightsResponse(
                    filter_type=filter_type.value,
                    recommendations=recommendations,
                    request_id=request_id
                )
                
                logger.info("Insights retrieved successfully",
                          filter_type=filter_type.value,
                          count=len(recommendations),
                          request_id=request_id)
                
                return result
                
            except (APIError, RateLimitError):
                raise
            except Exception as e:
                logger.error("Unexpected error getting insights",
                           filter_type=filter_type.value,
                           error=str(e),
                           request_id=request_id)
                raise TasteAPIError(f"Failed to get insights for {filter_type.value}: {e}")

    async def get_all_insights(self, request_id: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Get insights for all filter types with error handling"""
        filter_types = list(FilterType)
        
        async def safe_get_insights(ftype: FilterType) -> Tuple[str, Optional[InsightsResponse]]:
            """Safely get insights with individual error handling"""
            try:
                result = await self.get_insights(ftype, request_id)
                return ftype.value, result
            except Exception as e:
                logger.error("Failed to get insights for filter type",
                           filter_type=ftype.value,
                           error=str(e),
                           request_id=request_id)
                return ftype.value, None
        
        tasks = [safe_get_insights(ftype) for ftype in filter_types]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_recommendations = {}
        successful_count = 0
        
        for result in results:
            if isinstance(result, tuple):
                filter_type, insights_response = result
                if insights_response:
                    all_recommendations[f"{filter_type}_insights"] = [
                        rec.model_dump() for rec in insights_response.recommendations
                    ]
                    successful_count += 1
            else:
                logger.error("Unexpected result type", result=result, request_id=request_id)
        
        logger.info("All insights retrieved",
                   successful=successful_count,
                   total=len(filter_types),
                   request_id=request_id)
        
        return all_recommendations

    def get_metrics(self) -> Dict[str, Any]:
        """Get API usage metrics"""
        return {
            "total_requests": self.metrics.total_requests,
            "successful_requests": self.metrics.successful_requests,
            "failed_requests": self.metrics.failed_requests,
            "success_rate": self.metrics.success_rate,
            "average_response_time": self.metrics.average_response_time,
            "uptime_seconds": time.time() - self.metrics.start_time
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        try:
            result = await self.get_insights(FilterType.ARTIST)
            return {
                "status": "healthy",
                "api_responsive": True,
                "location": self.location,
                "timestamp": time.time()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "api_responsive": False,
                "error": str(e),
                "location": self.location,
                "timestamp": time.time()
            }


@asynccontextmanager
async def create_taste_api(location: str = None, config: TasteAPIConfig = None):
    """Context manager for TasteAPI with proper resource management"""
    api = TasteAPI(location=location, config=config)
    try:
        async with api:
            yield api
    except Exception as e:
        logger.error("Error in TasteAPI context manager", error=str(e))
        raise