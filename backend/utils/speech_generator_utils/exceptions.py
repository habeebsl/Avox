class SpeechGeneratorError(Exception):
    """Base exception for SpeechGenerator errors"""
    pass


class ConfigurationError(SpeechGeneratorError):
    """Raised when API is misconfigured"""
    pass


class VoiceNotFoundError(SpeechGeneratorError):
    """Raised when voice is not found"""
    pass


class QuotaExceededError(SpeechGeneratorError):
    """Raised when API quota is exceeded"""
    pass


class InvalidAudioError(SpeechGeneratorError):
    """Raised when audio data is invalid"""
    pass


class TextTooLongError(SpeechGeneratorError):
    """Raised when text exceeds maximum length"""
    pass