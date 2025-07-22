from pydantic import BaseModel, ValidationInfo, Field, field_validator
from typing import List, Optional

class InsightDetail(BaseModel):
    insight: str
    explanation: str

class ResultItem(BaseModel):
    voice_model: str
    music_prompt: str
    transcript: str
    insight_details: List[InsightDetail]

class ResponseSchema(BaseModel):
    results: List[ResultItem]


class Slang(BaseModel):
    slang: str
    pronounciation: str
    meaning: str
    usage_context: str
    example: str
    popularity: str
    region: str

class SlangsResponse(BaseModel):
    country: str
    slangs: list[Slang]
    sources: list[str]

class TranscriptRequest(BaseModel):
    user_prompt: str = Field(..., min_length=10)
    with_forecast: bool = Field(default=False)
    forecast_days: Optional[int] = Field(default=None, ge=1, le=14)
    variations: int = Field(default=3, ge=1, le=10)

    @field_validator('forecast_days')
    @classmethod
    def validate_forecast_days(cls, v: Optional[int], info: ValidationInfo) -> Optional[int]:
        wf = info.data.get('with_forecast', False)
        if wf and v is None:
            raise ValueError("`forecast_days` is required when `with_forecast=True`")
        if not wf and v is not None:
            raise ValueError("`forecast_days` should be None when `with_forecast=False`")
        return v

class SlangRequest(BaseModel):
    """Request model for slang generation"""
    country: str = Field(..., min_length=2, max_length=50)
    
    @field_validator('country')
    def validate_country(cls, v):
        if not v or not v.strip():
            raise ValueError("Country cannot be empty")
        
        if not v.replace(' ', '').isalpha():
            raise ValueError("Country name should contain only letters and spaces")
        
        return v.strip().title()