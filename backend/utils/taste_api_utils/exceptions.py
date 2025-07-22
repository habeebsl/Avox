class TasteAPIError(Exception):
    """Base exception for TasteAPI errors"""
    pass


class ConfigurationError(TasteAPIError):
    """Raised when API is misconfigured"""
    pass


class RateLimitError(TasteAPIError):
    """Raised when rate limit is exceeded"""
    pass


class APIError(TasteAPIError):
    """Raised when API returns an error"""
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data