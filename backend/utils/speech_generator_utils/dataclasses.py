from dataclasses import dataclass, field
from enum import Enum
import time


class OutputFormat(str, Enum):
    """Supported audio output formats"""
    MP3_22050_32 = "mp3_22050_32"
    MP3_44100_64 = "mp3_44100_64"
    MP3_44100_96 = "mp3_44100_96"
    MP3_44100_128 = "mp3_44100_128"
    MP3_44100_192 = "mp3_44100_192"
    PCM_16000 = "pcm_16000"
    PCM_22050 = "pcm_22050"
    PCM_24000 = "pcm_24000"
    PCM_44100 = "pcm_44100"
    ULAW_8000 = "ulaw_8000"


class VoiceType(str, Enum):
    """Voice types for search"""
    DEFAULT = "default"
    NON_DEFAULT = "non-default"
    CUSTOM = "custom"


@dataclass
class SpeechMetrics:
    """Track speech generation metrics"""
    total_generations: int = 0
    successful_generations: int = 0
    failed_generations: int = 0
    total_generation_time: float = 0.0
    total_audio_duration: float = 0.0
    voices_fetched: int = 0
    voice_clones_created: int = 0
    forced_alignments_processed: int = 0
    start_time: float = field(default_factory=time.time)

    @property
    def success_rate(self) -> float:
        return (self.successful_generations / self.total_generations) if self.total_generations > 0 else 0.0

    @property
    def average_generation_time(self) -> float:
        return (self.total_generation_time / self.successful_generations) if self.successful_generations > 0 else 0.0