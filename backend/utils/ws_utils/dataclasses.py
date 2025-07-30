from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Any, List

class StepStatus(Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class StepResult:
    status: StepStatus
    data: Optional[Any] = None
    error: Optional[str] = None
    step_name: str = ""

@dataclass 
class AdProcessingState:
    index: int
    location: str
    insights: StepResult
    transcript: StepResult
    speech: StepResult
    music: StepResult
    merge: StepResult
    voice_cleanup: StepResult