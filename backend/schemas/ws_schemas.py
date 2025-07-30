from typing import Literal, Optional, Union
from pydantic import BaseModel


AudioBuffer = bytes

class CountryData(BaseModel):
    code: str
    name: str

class AdRequest(BaseModel):
    product_name: str
    product_summary: str
    offer_summary: str
    cta: str
    locations: list[CountryData]
    ad_type: Literal["custom", "default"]
    slot_reservation_id: Optional[str]
    use_weather: bool
    forecast_type: Optional[Literal[1, 7, 14]]
    clone_language: Optional[str]
    