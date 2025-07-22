import os
from dotenv import load_dotenv
from utils.taste_api_utils.exceptions import ConfigurationError

load_dotenv()

class TasteAPIConfig:
    """Configuration management for TasteAPI"""
    
    def __init__(self):
        self.base_url = os.getenv('QLOO_BASE_URL', 'https://hackathon.api.qloo.com')
        self.api_key = os.getenv('QLOO_API_KEY')
        self.max_rate = int(os.getenv('QLOO_RATE_LIMIT', '3'))
        self.time_period = int(os.getenv('QLOO_TIME_PERIOD', '1'))
        self.timeout = int(os.getenv('QLOO_TIMEOUT', '30'))
        self.max_retries = int(os.getenv('QLOO_MAX_RETRIES', '3'))
        self.max_recommendations = int(os.getenv('QLOO_MAX_RECOMMENDATIONS', '3'))
        self.max_tags = int(os.getenv('QLOO_MAX_TAGS', '7'))
        
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration"""
        if not self.api_key:
            raise ConfigurationError("QLOO_API_KEY environment variable is required")
        
        if not self.base_url:
            raise ConfigurationError("QLOO_BASE_URL is required")
        
        if self.max_rate <= 0:
            raise ConfigurationError("Rate limit must be positive")