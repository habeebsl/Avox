import os
from dotenv import load_dotenv
from utils.speech_generator_utils.dataclasses import OutputFormat
from utils.speech_generator_utils.exceptions import ConfigurationError

load_dotenv()

class SpeechGeneratorConfig:
    """Configuration for SpeechGenerator"""
    
    def __init__(self):
        self.api_key = os.getenv('ELEVENLABS_API_KEY')
        self.model = os.getenv('ELEVENLABS_MODEL', 'eleven_multilingual_v2')
        self.default_output_format = OutputFormat(os.getenv('ELEVENLABS_OUTPUT_FORMAT', 'mp3_44100_128'))
        self.default_speed = float(os.getenv('ELEVENLABS_DEFAULT_SPEED', '1.12'))
        self.max_text_length = int(os.getenv('ELEVENLABS_MAX_TEXT_LENGTH', '50000'))
        self.request_timeout = int(os.getenv('ELEVENLABS_TIMEOUT', '60'))
        self.max_retries = int(os.getenv('ELEVENLABS_MAX_RETRIES', '3'))
        self.chunk_size = int(os.getenv('ELEVENLABS_CHUNK_SIZE', '8192'))
        
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration"""
        if not self.api_key:
            raise ConfigurationError("ELEVENLABS_API_KEY environment variable is required")
        
        if self.default_speed < 0.25 or self.default_speed > 4.0:
            raise ConfigurationError("Default speed must be between 0.25 and 4.0")
        
        if self.max_text_length <= 0 or self.max_text_length > 500000:
            raise ConfigurationError("Max text length must be between 1 and 500000")