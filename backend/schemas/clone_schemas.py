from pydantic import BaseModel
from typing import Optional

class ReservationResponse(BaseModel):
    reservation_id: Optional[str]
    created: bool
    detail: Optional[str]

class CloningSentencesResponse(BaseModel):
    sentences: list[str]
    language: str