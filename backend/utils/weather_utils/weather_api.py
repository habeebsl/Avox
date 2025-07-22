import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager
import time

import httpx
from dotenv import load_dotenv
import tenacity
import structlog

from schemas.weather_schemas import ForecastData, HistoricalWeatherData
from utils.weather_utils.config import WeatherAPIConfig
from utils.weather_utils.dataclasses import WeatherMetrics
from utils.weather_utils.exceptions import (
    APIQuotaExceededError, 
    LocationNotFoundError, 
    WeatherAPIError, 
    ConfigurationError, 
    APIError)
from utils.weather_utils.helpers import (
    LocationCache, 
    days_forward_from_today, 
    safe_float, 
    safe_int)

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

class WeatherAPI:
    """Production-ready Weather API client"""

    def __init__(self, config: Optional[WeatherAPIConfig] = None):
        self.config = config or WeatherAPIConfig()
        self.metrics = WeatherMetrics()
        self._client: Optional[httpx.AsyncClient] = None
        self._location_cache = LocationCache(self.config.cache_ttl_seconds)
        
        logger.info("WeatherAPI initialized", 
                   base_url=self.config.base_url,
                   timeout=self.config.timeout)

    async def __aenter__(self):
        """Create shared HTTP client when entering context"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
                headers={"User-Agent": "WeatherAPI-Client/1.0"}
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Properly close HTTP client when exiting context"""
        if self._client:
            await self._client.aclose()
            self._client = None

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
        retry=tenacity.retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
        reraise=True
    )
    async def _make_request(
        self, 
        url: str, 
        params: Dict[str, Any], 
        request_id: str = None
    ) -> httpx.Response:
        """Make HTTP request with comprehensive error handling"""
        start_time = time.time()
        self.metrics.total_requests += 1
        
        if not self._client:
            raise WeatherAPIError("HTTP client not initialized. Use async context manager.")
        
        try:
            logger.info("Making weather API request", 
                       url=url, 
                       location=params.get('q'),
                       request_id=request_id)
            
            response = await self._client.get(url, params=params)
            
            response_time = time.time() - start_time
            self.metrics.total_response_time += response_time
            
            if response.status_code == 200:
                self.metrics.successful_requests += 1
                logger.info("Weather API request successful", 
                          status_code=response.status_code,
                          response_time=response_time,
                          request_id=request_id)
                return response
            elif response.status_code == 400:
                self.metrics.failed_requests += 1
                error_data = response.json() if response.headers.get("content-type") == "application/json" else {}
                error_code = error_data.get('error', {}).get('code', 0)
                
                if error_code == 1006:  # Location not found
                    logger.error("Location not found", 
                               location=params.get('q'),
                               request_id=request_id)
                    raise LocationNotFoundError(f"Location not found: {params.get('q')}")
                else:
                    logger.error("Bad request", 
                               error_data=error_data,
                               request_id=request_id)
                    raise APIError("Invalid request parameters", 400, error_data)
            elif response.status_code == 401:
                self.metrics.failed_requests += 1
                logger.error("API key invalid or missing", request_id=request_id)
                raise ConfigurationError("Invalid API key")
            elif response.status_code == 403:
                self.metrics.failed_requests += 1
                logger.error("API quota exceeded", request_id=request_id)
                raise APIQuotaExceededError("API quota exceeded")
            elif response.status_code >= 500:
                self.metrics.failed_requests += 1
                logger.error("Weather API server error", 
                           status_code=response.status_code,
                           request_id=request_id)
                raise APIError(f"Server error: {response.status_code}", response.status_code)
            else:
                self.metrics.failed_requests += 1
                logger.error("Weather API error",
                           status_code=response.status_code,
                           response_text=response.text[:200],
                           request_id=request_id)
                raise APIError(f"API error: {response.status_code}", response.status_code)
                
        except httpx.TimeoutException as e:
            self.metrics.failed_requests += 1
            logger.error("Weather API timeout", error=str(e), request_id=request_id)
            raise APIError(f"Request timeout: {e}")
        except httpx.RequestError as e:
            self.metrics.failed_requests += 1
            logger.error("Weather API request error", error=str(e), request_id=request_id)
            raise APIError(f"Request error: {e}")

    def _validate_location(self, location: str) -> str:
        """Validate and normalize location"""
        if not location or not location.strip():
            raise ValueError("Location cannot be empty")
        
        location = location.strip()
        if len(location) < 2:
            raise ValueError("Location must be at least 2 characters")
        
        if len(location) > 100:
            raise ValueError("Location cannot exceed 100 characters")
        
        return location

    def _validate_days(self, days: int, max_days: int, operation: str) -> int:
        """Validate days parameter"""
        if not isinstance(days, int) or days <= 0:
            raise ValueError(f"Days must be a positive integer for {operation}")
        
        if days > max_days:
            logger.warning(f"Days exceeds maximum for {operation}",
                          requested=days, maximum=max_days)
            return max_days
        
        return days

    def _normalize_location(self, location: str) -> str:
        """Normalize location using cache"""
        location = self._validate_location(location)
        
        cached_location = self._location_cache.get(location)
        if cached_location:
            self.metrics.location_cache_hits += 1
            return cached_location
        
        self.metrics.location_cache_misses += 1

        normalized = location.title()
        self._location_cache.set(location, normalized)
        
        return normalized

    def format_forecast_data(self, date: str, data: Dict[str, Any]) -> ForecastData:
        """Format forecast data with comprehensive error handling"""
        try:
            if not isinstance(data, dict):
                raise ValueError("Invalid data format")
            
            forecast_day = days_forward_from_today(date)
            day_label = "Today" if forecast_day == 0 else f"Day {forecast_day}"
            
            condition = data.get('condition', {})
            if not isinstance(condition, dict):
                condition = {}
            
            weather_description = condition.get('text', 'Unknown').strip()
            if not weather_description:
                weather_description = 'Unknown'
            
            forecast_data = ForecastData(
                forecast_day=day_label,
                average_temp_in_celcius=safe_float(data.get('avgtemp_c')),
                average_humidity=safe_int(data.get('avghumidity')),
                weather_description=weather_description
            )
            
            return forecast_data
            
        except Exception as e:
            logger.warning("Error formatting forecast data", 
                        error=str(e), 
                        date=date,
                        data_keys=list(data.keys()) if isinstance(data, dict) else None)
            
            return ForecastData(
                forecast_day=f"Day {days_forward_from_today(date)}",
                weather_description="Data unavailable"
            )

    def _format_historical_data(self, date: str, data: Dict[str, Any]) -> HistoricalWeatherData:
        """Format historical weather data"""
        try:
            condition = data.get('condition', {})
            if not isinstance(condition, dict):
                condition = {}
            
            weather_description = condition.get('text', 'Unknown').strip()
            if not weather_description:
                weather_description = 'Unknown'
            
            return HistoricalWeatherData(
                date=date,
                average_temp_in_celcius=safe_float(data.get('avgtemp_c')),
                average_humidity=safe_int(data.get('avghumidity')),
                weather_description=weather_description
            )
            
        except Exception as e:
            logger.warning("Error formatting historical data", 
                        error=str(e), date=date)
            
            return HistoricalWeatherData(
                date=date,
                weather_description="Data unavailable"
            )

    async def get_weather_history(
        self, 
        location: str, 
        day: int,
        request_id: str = None
    ) -> Optional[HistoricalWeatherData]:
        """Get weather history for a specific day with error handling"""
        try:
            location = self._normalize_location(location)
            
            if day < 1:
                raise ValueError("Day must be at least 1 (yesterday)")
            
            if day > self.config.max_history_days:
                raise ValueError(f"Day cannot exceed {self.config.max_history_days}")
            
            date = (datetime.now(timezone.utc) - timedelta(days=day)).strftime('%Y-%m-%d')

            params = {
                "key": self.config.api_key,
                "q": location,
                "dt": date
            }

            url = f"{self.config.base_url}/history.json"

            response = await self._make_request(url, params, request_id)
            response_data = response.json()
            
            forecast_data = response_data.get("forecast", {})
            forecast_day = forecast_data.get("forecastday", [])
            
            if not forecast_day:
                logger.warning("No forecast data in response", 
                              location=location, date=date, request_id=request_id)
                return None
            
            day_data = forecast_day[0].get("day", {})
            return self._format_historical_data(date, day_data)
            
        except (LocationNotFoundError, APIQuotaExceededError, ConfigurationError):
            # Re-raise specific errors
            raise
        except Exception as e:
            logger.error("Error getting weather history",
                        location=location,
                        day=day,
                        error=str(e),
                        request_id=request_id)
            return None

    async def get_all_weather_history(
        self, 
        location: str, 
        days: int,
        request_id: str = None
    ) -> List[Optional[HistoricalWeatherData]]:
        """Get weather history for multiple days with error handling"""
        try:
            location = self._normalize_location(location)
            days = self._validate_days(days, self.config.max_history_days, "history")
            
            async def safe_get_history(day_offset: int) -> Optional[HistoricalWeatherData]:
                """Safely get history for one day"""
                try:
                    return await self.get_weather_history(location, day_offset, request_id)
                except Exception as e:
                    logger.error("Failed to get history for day",
                               day=day_offset,
                               location=location,
                               error=str(e),
                               request_id=request_id)
                    return None

            tasks = [
                safe_get_history(day_offset) 
                for day_offset in range(1, days + 1)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=False)
            
            # Filter out None results
            valid_results = [result for result in results if result is not None]
            
            logger.info("Weather history retrieved",
                       location=location,
                       requested_days=days,
                       successful_days=len(valid_results),
                       request_id=request_id)
            
            return results
            
        except Exception as e:
            logger.error("Error getting all weather history",
                        location=location,
                        days=days,
                        error=str(e),
                        request_id=request_id)
            return []

    async def get_forecast(
        self, 
        location: str, 
        days: int,
        request_id: str = None
    ) -> List[ForecastData]:
        """Get weather forecast with comprehensive error handling"""
        try:
            location = self._normalize_location(location)
            days = self._validate_days(days, self.config.max_forecast_days, "forecast")

            params = {
                "key": self.config.api_key,
                "q": location,
                "days": days
            }

            url = f"{self.config.base_url}/forecast.json"
            response = await self._make_request(url, params, request_id)
            response_data = response.json()

            forecast_data = []
            forecast_days = response_data.get("forecast", {}).get("forecastday", [])
            
            if not forecast_days:
                logger.warning("No forecast data in response",
                              location=location,
                              request_id=request_id)
                return []

            for day_data in forecast_days:
                if not isinstance(day_data, dict):
                    continue
                    
                date = day_data.get('date')
                day = day_data.get('day', {})
                
                if date and isinstance(day, dict):
                    formatted = self.format_forecast_data(date, day)
                    forecast_data.append(formatted)

            logger.info("Weather forecast retrieved",
                       location=location,
                       days=len(forecast_data),
                       request_id=request_id)
            
            return forecast_data
            
        except (LocationNotFoundError, APIQuotaExceededError, ConfigurationError):
            # Re-raise specific errors
            raise
        except Exception as e:
            logger.error("Error getting weather forecast",
                        location=location,
                        days=days,
                        error=str(e),
                        request_id=request_id)
            return []

    async def get_current_weather(
        self, 
        location: str,
        request_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """Get current weather conditions"""
        try:
            location = self._normalize_location(location)
            
            params = {
                "key": self.config.api_key,
                "q": location
            }
            
            url = f"{self.config.base_url}/current.json"
            response = await self._make_request(url, params, request_id)
            response_data = response.json()
            
            current = response_data.get("current", {})
            location_data = response_data.get("location", {})
            
            if not current:
                logger.warning("No current weather data in response",
                              location=location,
                              request_id=request_id)
                return None
            
            return {
                "location": {
                    "name": location_data.get("name"),
                    "region": location_data.get("region"),
                    "country": location_data.get("country")
                },
                "temperature_celsius": safe_float(current.get("temp_c")),
                "feels_like_celsius": safe_float(current.get("feelslike_c")),
                "humidity": safe_int(current.get("humidity")),
                "weather_description": current.get("condition", {}).get("text", "Unknown"),
                "wind_kph": safe_float(current.get("wind_kph")),
                "last_updated": current.get("last_updated")
            }
            
        except Exception as e:
            logger.error("Error getting current weather",
                        location=location,
                        error=str(e),
                        request_id=request_id)
            return None

    def get_metrics(self) -> Dict[str, Any]:
        """Get API usage metrics"""
        self._location_cache.clear_expired()
        
        return {
            "total_requests": self.metrics.total_requests,
            "successful_requests": self.metrics.successful_requests,
            "failed_requests": self.metrics.failed_requests,
            "success_rate": self.metrics.success_rate,
            "average_response_time": self.metrics.average_response_time,
            "uptime_seconds": time.time() - self.metrics.start_time,
            "cache_hit_rate": self.metrics.cache_hit_rate,
            "cached_locations": len(self._location_cache._cache)
        }

    async def health_check(self, test_location: str = "London") -> Dict[str, Any]:
        """Perform health check"""
        try:
            result = await self.get_current_weather(test_location)
            return {
                "status": "healthy",
                "api_responsive": result is not None,
                "test_location": test_location,
                "timestamp": time.time()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "api_responsive": False,
                "error": str(e),
                "test_location": test_location,
                "timestamp": time.time()
            }


@asynccontextmanager
async def create_weather_api(config: WeatherAPIConfig = None):
    """Context manager for WeatherAPI with proper resource management"""
    api = WeatherAPI(config=config)
    try:
        async with api:
            yield api
    except Exception as e:
        logger.error("Error in WeatherAPI context manager", error=str(e))
        raise