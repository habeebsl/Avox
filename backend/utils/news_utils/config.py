import os
from dotenv import load_dotenv

from utils.news_utils.exceptions import ConfigurationError

load_dotenv()

class NewsAPIConfig:
    """Configuration for NewsAPI"""
    
    def __init__(self):
        self.api_key = os.getenv('SERPER_API_KEY')
        self.base_url = os.getenv('SERPER_BASE_URL', 'https://google.serper.dev/news')
        self.timeout = int(os.getenv('NEWS_TIMEOUT', '30'))
        self.max_retries = int(os.getenv('NEWS_MAX_RETRIES', '3'))
        self.max_articles_per_query = int(os.getenv('NEWS_MAX_ARTICLES', '3'))
        self.max_concurrent_queries = int(os.getenv('NEWS_MAX_CONCURRENT', '10'))
        
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration"""
        if not self.api_key:
            raise ConfigurationError("SERPER_API_KEY environment variable is required")
        
        if not self.base_url:
            raise ConfigurationError("News API base URL is required")
        
        if self.max_articles_per_query <= 0:
            raise ConfigurationError("Max articles per query must be positive")
        
        if self.max_concurrent_queries <= 0:
            raise ConfigurationError("Max concurrent queries must be positive")
