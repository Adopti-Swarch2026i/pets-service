"""
Global exception handlers for FastAPI.

Translates domain exceptions (pure Python) into proper HTTP responses.
This is the ONLY place where HTTP status codes are mapped to domain errors.
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.exceptions.pet_exceptions import (
    PetNotFoundError,
    NotPetOwnerError,
    InvalidTokenError,
)


async def pet_not_found_handler(_request: Request, exc: PetNotFoundError):
    return JSONResponse(status_code=404, content={"detail": exc.detail})


async def not_pet_owner_handler(_request: Request, exc: NotPetOwnerError):
    return JSONResponse(status_code=403, content={"detail": exc.detail})


async def invalid_token_handler(_request: Request, exc: InvalidTokenError):
    return JSONResponse(status_code=401, content={"detail": exc.detail})
