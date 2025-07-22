from typing import List, Optional, Union
from pydantic import BaseModel, Field

class Topic(BaseModel):
    query: str = Field(min_length=1)
    country: str = Field(min_length=2, max_length=2)
    timestamp: Optional[int] = Field(None, ge=0)
    formatted_timestamp: Optional[str] = None
    search_volume: Optional[int] = Field(None, ge=0)
    related_queries: List[str] = Field(default_factory=list)
    category: Optional[Union[str, int]] = None
