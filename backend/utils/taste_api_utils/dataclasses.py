from dataclasses import dataclass, field
from enum import Enum
import time


class FilterType(str, Enum):
    """Supported filter types for insights"""
    ARTIST = "artist"
    BOOK = "book"
    MOVIE = "movie"
    PLACE = "place"
    TV_SHOW = "tv_show"
    BRAND = "brand"

@dataclass
class APIMetrics:
    """Track API usage metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    start_time: float = field(default_factory=time.time)

    @property
    def success_rate(self) -> float:
        return (self.successful_requests / self.total_requests) if self.total_requests > 0 else 0.0

    @property
    def average_response_time(self) -> float:
        return (self.total_response_time / self.successful_requests) if self.successful_requests > 0 else 0.0
