import time
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class NewsArticle(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    snippet: Optional[str] = Field(None, max_length=1000)
    
    @field_validator('title')
    def validate_title(cls, v):
        return v.strip() if v else ""
    
    @field_validator('snippet')
    def validate_snippet(cls, v):
        return v.strip() if v else None


class NewsResponse(BaseModel):
    query: str = Field(..., min_length=1)
    articles: List[NewsArticle] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)
    request_id: Optional[str] = None
    
    @field_validator('query')
    def validate_query(cls, v):
        return v.strip()