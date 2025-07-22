import time
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class RecommendationItem(BaseModel):
    """Pydantic model for recommendation items"""
    name: str = Field(..., min_length=1, max_length=200)
    tags: List[str] = Field(default_factory=list, max_items=10)
    popularity: Optional[float] = Field(None, ge=0.0, le=1.0)

    @field_validator('tags')
    def validate_tags(cls, v: List[str]) -> List[str]:
        return [tag.strip() for tag in v if tag and tag.strip()]


class InsightsResponse(BaseModel):
    """Pydantic model for insights response"""
    filter_type: str
    recommendations: List[RecommendationItem]
    timestamp: float = Field(default_factory=time.time)
    request_id: Optional[str] = None