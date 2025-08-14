"""
Custom exceptions for the ODRAS application.
"""


class ODRASException(Exception):
    """Base exception for ODRAS application."""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class ConfigurationError(ODRASException):
    """Raised when there's a configuration error."""
    pass


class ServiceError(ODRASException):
    """Raised when a service encounters an error."""
    pass


class ValidationError(ODRASException):
    """Raised when data validation fails."""
    pass


class PersistenceError(ODRASException):
    """Raised when data persistence operations fail."""
    pass


class LLMError(ODRASException):
    """Raised when LLM operations fail."""
    pass


class FileProcessingError(ODRASException):
    """Raised when file processing operations fail."""
    pass


class WorkflowError(ODRASException):
    """Raised when workflow operations fail."""
    pass
