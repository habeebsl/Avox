class MusicGenError(Exception):
    """Base exception for MusicGen errors"""
    pass


class ConfigurationError(MusicGenError):
    """Configuration-related errors"""
    pass


class GenerationError(MusicGenError):
    """Music generation errors"""
    pass


class DownloadError(MusicGenError):
    """Audio download errors"""
    pass