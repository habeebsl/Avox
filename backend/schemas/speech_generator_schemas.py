from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator


class VoiceData(BaseModel):
    voice_name: str = Field(..., min_length=1, max_length=100)
    voice_id: str = Field(..., min_length=1)
    description: Optional[str] = None
    labels: Optional[Dict[str, Any]] = None
    category: Optional[str] = None
    
    @field_validator('voice_name')
    def validate_voice_name(cls, v):
        return v.strip()


class SpeechRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50000)
    voice_id: str = Field(..., min_length=1)
    speed: float = Field(default=1.12, ge=0.25, le=4.0)
    stability: Optional[float] = Field(None, ge=0.0, le=1.0)
    similarity_boost: Optional[float] = Field(None, ge=0.0, le=1.0)
    style: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    @field_validator('text')
    def validate_text(cls, v):
        text = v.strip()
        if not text:
            raise ValueError("Text cannot be empty")

        if len(text.encode('utf-8')) > 200000:  # ~200KB limit
            raise ValueError("Text too long")
        return text
