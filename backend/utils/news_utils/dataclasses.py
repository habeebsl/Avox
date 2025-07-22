from dataclasses import dataclass, field
import time

@dataclass
class NewsMetrics:
    """Track news API usage metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    start_time: float = field(default_factory=time.time)
    queries_processed: int = 0
    articles_retrieved: int = 0

    @property
    def success_rate(self) -> float:
        return (self.successful_requests / self.total_requests) if self.total_requests > 0 else 0.0

    @property
    def average_response_time(self) -> float:
        return (self.total_response_time / self.successful_requests) if self.successful_requests > 0 else 0.0

    @property
    def average_articles_per_query(self) -> float:
        return (self.articles_retrieved / self.queries_processed) if self.queries_processed > 0 else 0.0