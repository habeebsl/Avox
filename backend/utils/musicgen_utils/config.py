import os
import structlog
from dotenv import load_dotenv

from utils.musicgen_utils.dataclasses import ModelVersion, NormalizationStrategy, OutputFormat

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

class MusicGenConfig:
    """Configuration for MusicGen"""
    
    def __init__(self):
        self.replicate_token = os.getenv('REPLICATE_API_TOKEN')
        
        self.default_model = ModelVersion(os.getenv('MUSICGEN_MODEL', 'stereo-large'))
        self.max_duration = int(os.getenv('MUSICGEN_MAX_DURATION', '120'))  # seconds
        self.min_duration = int(os.getenv('MUSICGEN_MIN_DURATION', '5'))   # seconds
        self.timeout = int(os.getenv('MUSICGEN_TIMEOUT', '300'))           # 5 minutes
        self.download_timeout = int(os.getenv('MUSICGEN_DOWNLOAD_TIMEOUT', '60'))  # 1 minute
        
        self.default_format = OutputFormat(os.getenv('MUSICGEN_FORMAT', 'mp3'))
        self.default_normalization = NormalizationStrategy(os.getenv('MUSICGEN_NORMALIZATION', 'peak'))
        
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration"""
        if not self.replicate_token:
            logger.warning("REPLICATE_API_TOKEN not set, may cause authentication issues")
        
        if self.max_duration > 300:  # 5 minutes
            logger.warning("Max duration is very high, may cause timeouts")
