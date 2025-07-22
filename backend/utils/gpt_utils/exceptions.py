class GPTError(Exception):
    """Base exception for GPT-related errors"""
    pass


class ConfigurationError(GPTError):
    """Raised when GPT is misconfigured"""
    pass


class APIQuotaError(GPTError):
    """Raised when OpenAI API quota is exceeded"""
    pass


class ModelNotFoundError(GPTError):
    """Raised when specified model is not available"""
    pass


class RateLimitError(GPTError):
    """Raised when rate limit is exceeded"""
    pass


class TokenLimitError(GPTError):
    """Raised when token limit is exceeded"""
    pass


class ContentFilterError(GPTError):
    """Raised when content is filtered by OpenAI"""
    pass