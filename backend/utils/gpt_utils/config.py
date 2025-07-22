import os
from dotenv import load_dotenv

from utils.gpt_utils.dataclasses import GPTModel
from utils.gpt_utils.exceptions import ConfigurationError

load_dotenv()

class GPTConfig:
    """Configuration for GPT client"""
    
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.organization = os.getenv('OPENAI_ORGANIZATION')
        self.model = os.getenv('GPT_MODEL', GPTModel.GPT_4_1.value)
        self.timeout = float(os.getenv('GPT_TIMEOUT', '60.0'))
        self.max_retries = int(os.getenv('GPT_MAX_RETRIES', '3'))
        self.max_tokens = int(os.getenv('GPT_MAX_TOKENS', '4000'))
        self.temperature = float(os.getenv('GPT_TEMPERATURE', '0.7'))
        self.request_timeout = float(os.getenv('GPT_REQUEST_TIMEOUT', '120.0'))
        
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration"""
        if not self.api_key:
            raise ConfigurationError("OPENAI_API_KEY environment variable is required")
        
        if self.temperature < 0.0 or self.temperature > 2.0:
            raise ConfigurationError("Temperature must be between 0.0 and 2.0")
        
        if self.max_tokens < 1 or self.max_tokens > 8192:
            raise ConfigurationError("Max tokens must be between 1 and 8192")