"""
Custom domain exceptions for the Pets Service.

These are pure Python exceptions — completely decoupled from
any HTTP framework. The translation to HTTP status codes happens
in error_handlers.py via FastAPI exception handlers.
"""


class PetServiceError(Exception):
    """Base exception for all domain errors in the Pets Service."""

    def __init__(self, detail: str = "An unexpected error occurred"):
        self.detail = detail
        super().__init__(self.detail)


class PetNotFoundError(PetServiceError):
    """Raised when a pet/report is not found in the database."""

    def __init__(self, detail: str = "Pet report not found"):
        super().__init__(detail)


class NotPetOwnerError(PetServiceError):
    """Raised when the authenticated user is not the owner of the resource."""

    def __init__(self, detail: str = "You are not the owner of this resource"):
        super().__init__(detail)


class InvalidTokenError(PetServiceError):
    """Raised when the authentication token is missing or invalid."""

    def __init__(self, detail: str = "Invalid or missing authentication token"):
        super().__init__(detail)
