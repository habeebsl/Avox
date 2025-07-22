class MixerError(Exception):
    """Base exception for audio mixer errors"""
    pass


class AudioFormatError(MixerError):
    """Raised when audio format is not supported or corrupted"""
    pass


class AudioProcessingError(MixerError):
    """Raised when audio processing fails"""
    pass


class ConfigurationError(MixerError):
    """Raised when mixer is misconfigured"""
    pass
