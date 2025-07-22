from dataclasses import dataclass, field
import time


@dataclass
class WeatherMetrics:
    """Track weather API usage metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    start_time: float = field(default_factory=time.time)
    location_cache_hits: int = 0
    location_cache_misses: int = 0

    @property
    def success_rate(self) -> float:
        return (self.successful_requests / self.total_requests) if self.total_requests > 0 else 0.0

    @property
    def average_response_time(self) -> float:
        return (self.total_response_time / self.successful_requests) if self.successful_requests > 0 else 0.0

    @property
    def cache_hit_rate(self) -> float:
        total_cache_ops = self.location_cache_hits + self.location_cache_misses
        return (self.location_cache_hits / total_cache_ops) if total_cache_ops > 0 else 0.0