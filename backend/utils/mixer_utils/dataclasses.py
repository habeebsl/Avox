from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import tempfile
import time
from typing import List, Optional

from utils.mixer_utils.exceptions import ConfigurationError


class AudioFormat(str, Enum):
    """Supported audio formats"""
    MP3 = "mp3"
    WAV = "wav"
    M4A = "m4a"
    FLAC = "flac"
    OGG = "ogg"
    AAC = "aac"

@dataclass
class MixerMetrics:
    """Track mixer performance metrics"""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_processing_time: float = 0.0
    start_time: float = field(default_factory=time.time)
    
    merge_operations: int = 0
    duration_operations: int = 0
    format_conversions: int = 0
    
    @property
    def success_rate(self) -> float:
        return (self.successful_operations / self.total_operations) if self.total_operations > 0 else 0.0
    
    @property
    def average_processing_time(self) -> float:
        return (self.total_processing_time / self.successful_operations) if self.successful_operations > 0 else 0.0


@dataclass
class MixerConfig:
    """Configuration for audio mixer"""
    max_file_size_mb: int = 100
    max_duration_minutes: int = 30
    default_fade_duration_ms: int = 2000
    default_music_reduction_db: float = 13.0
    music_extension_ms: int = 1000
    supported_formats: List[AudioFormat] = field(default_factory=lambda: list(AudioFormat))
    temp_dir: Optional[Path] = None
    enable_ffmpeg_check: bool = True
    
    def __post_init__(self):
        if self.temp_dir is None:
            self.temp_dir = Path(tempfile.gettempdir())
        
        if self.max_file_size_mb <= 0:
            raise ConfigurationError("max_file_size_mb must be positive")
        
        if self.max_duration_minutes <= 0:
            raise ConfigurationError("max_duration_minutes must be positive")
        
        if self.default_fade_duration_ms < 0:
            raise ConfigurationError("default_fade_duration_ms cannot be negative")


@dataclass
class AudioInfo:
    """Information about an audio file"""
    duration_ms: int
    duration_seconds: float
    channels: int
    sample_rate: int
    frame_rate: int
    format: str
    file_size_bytes: Optional[int] = None
    
    @property
    def duration_minutes(self) -> float:
        return self.duration_seconds / 60.0

