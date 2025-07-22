from dataclasses import dataclass, field
from enum import Enum
import time

class GPTModel(str, Enum):
    """Supported GPT models"""
    GPT_4_TURBO = "gpt-4-turbo-preview"
    GPT_4 = "gpt-4"
    GPT_4_1 = "gpt-4.1"
    GPT_3_5_TURBO = "gpt-3.5-turbo"

@dataclass
class GPTMetrics:
    """Track GPT API usage metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens_used: int = 0
    total_response_time: float = 0.0
    start_time: float = field(default_factory=time.time)
    transcript_requests: int = 0
    slang_requests: int = 0
    rate_limit_hits: int = 0

    @property
    def success_rate(self) -> float:
        return (self.successful_requests / self.total_requests) if self.total_requests > 0 else 0.0

    @property
    def average_response_time(self) -> float:
        return (self.total_response_time / self.successful_requests) if self.successful_requests > 0 else 0.0

    @property
    def average_tokens_per_request(self) -> float:
        return (self.total_tokens_used / self.successful_requests) if self.successful_requests > 0 else 0.0
