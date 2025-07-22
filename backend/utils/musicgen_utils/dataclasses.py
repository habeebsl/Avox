from dataclasses import dataclass, field
from enum import Enum
import time


class ModelVersion(str, Enum):
    """Available MusicGen model versions"""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    STEREO_LARGE = "stereo-large"


class OutputFormat(str, Enum):
    """Supported output formats"""
    MP3 = "mp3"
    WAV = "wav"


class NormalizationStrategy(str, Enum):
    """Audio normalization strategies"""
    LOUDNESS = "loudness"
    PEAK = "peak"
    CLIP = "clip"
    NONE = "none"


@dataclass
class MusicGenMetrics:
    """Track MusicGen usage metrics"""
    total_generations: int = 0
    successful_generations: int = 0
    failed_generations: int = 0
    total_generation_time: float = 0.0
    total_download_time: float = 0.0
    start_time: float = field(default_factory=time.time)

    @property
    def success_rate(self) -> float:
        return (self.successful_generations / self.total_generations) if self.total_generations > 0 else 0.0

    @property
    def average_generation_time(self) -> float:
        return (self.total_generation_time / self.successful_generations) if self.successful_generations > 0 else 0.0