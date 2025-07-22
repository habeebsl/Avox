import os
from dotenv import load_dotenv
import structlog
from utils.weather_utils.exceptions import ConfigurationError

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

class WeatherAPIConfig:
    """Configuration for WeatherAPI"""
    
    def __init__(self):
        self.base_url = os.getenv('WEATHER_BASE_URL', 'http://api.weatherapi.com/v1')
        self.api_key = os.getenv('WEATHER_API_KEY')
        self.timeout = int(os.getenv('WEATHER_TIMEOUT', '30'))
        self.max_retries = int(os.getenv('WEATHER_MAX_RETRIES', '3'))
        self.max_forecast_days = int(os.getenv('WEATHER_MAX_FORECAST_DAYS', '10'))
        self.max_history_days = int(os.getenv('WEATHER_MAX_HISTORY_DAYS', '30'))
        self.cache_ttl_seconds = int(os.getenv('WEATHER_CACHE_TTL', '300'))  # 5 minutes
        
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration"""
        if not self.api_key:
            raise ConfigurationError("WEATHER_API_KEY environment variable is required")
        
        if not self.base_url:
            raise ConfigurationError("Weather API base URL is required")
        
        if self.max_forecast_days > 10:
            logger.warning("Max forecast days exceeds API limit, setting to 10")
            self.max_forecast_days = 10
