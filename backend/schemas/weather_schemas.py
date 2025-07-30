from typing import Optional
from pydantic import BaseModel, Field, field_validator


class WeatherCondition(BaseModel):
    text: str = Field(..., min_length=1, max_length=100)
    icon: Optional[str] = None
    code: Optional[int] = None


class ForecastData(BaseModel):
    forecast_day: str = Field(..., min_length=1)
    average_temp_in_celcius: Optional[float] = Field(None, ge=-50, le=60)
    average_humidity: Optional[int] = Field(None, ge=0, le=100)
    weather_description: str = Field(..., min_length=1)
    
    @field_validator('forecast_day')
    def validate_forecast_day(cls, v):
        return v.strip()

    @field_validator('weather_description')
    def validate_weather_description(cls, v):
        return v.strip()
    

class HistoricalWeatherData(BaseModel):
    date: str
    average_temp_in_celcius: Optional[float] = Field(None, ge=-50, le=60)
    average_humidity: Optional[int] = Field(None, ge=0, le=100)
    weather_description: str = Field(..., min_length=1)
