class WeatherAPIError(Exception):
    """Base exception for WeatherAPI errors"""
    pass


class ConfigurationError(WeatherAPIError):
    """Raised when API is misconfigured"""
    pass


class LocationNotFoundError(WeatherAPIError):
    """Raised when location is not found"""
    pass


class APIQuotaExceededError(WeatherAPIError):
    """Raised when API quota is exceeded"""
    pass


class APIError(WeatherAPIError):
    """Raised when API returns an error"""
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data