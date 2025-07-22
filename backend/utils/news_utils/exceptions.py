class NewsAPIError(Exception):
    """Base exception for NewsAPI errors"""
    pass


class ConfigurationError(NewsAPIError):
    """Raised when API is misconfigured"""
    pass


class APIQuotaExceededError(NewsAPIError):
    """Raised when API quota is exceeded"""
    pass


class InvalidQueryError(NewsAPIError):
    """Raised when query is invalid"""
    pass


class APIError(NewsAPIError):
    """Raised when API returns an error"""
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data