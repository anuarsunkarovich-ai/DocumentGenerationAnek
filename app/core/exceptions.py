"""Application-specific exception classes."""


class ApplicationError(Exception):
    """Base exception for domain-specific failures."""


class NotFoundError(ApplicationError):
    """Raised when a requested resource does not exist."""


class ConflictError(ApplicationError):
    """Raised when a resource already exists or cannot be created safely."""


class ValidationError(ApplicationError):
    """Raised when a request violates a business rule."""


class AuthenticationError(ApplicationError):
    """Raised when a request is missing valid authentication."""


class AuthorizationError(ApplicationError):
    """Raised when an authenticated user lacks access to a resource."""
