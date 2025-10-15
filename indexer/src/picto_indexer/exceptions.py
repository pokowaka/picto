"""
Defines custom exceptions for the Picto Indexer application.
"""

class PictoIndexerError(Exception):
    """Base exception for all application-specific errors."""
    pass

class APIError(PictoIndexerError):
    """Raised for errors related to the Gemini API communication."""
    pass

class FileSystemError(PictoIndexerError):
    """Raised for errors related to file system operations."""
    pass

class ConfigurationError(PictoIndexerError):
    """Raised for configuration-related errors."""
    pass
