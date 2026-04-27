import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.cloudinary_config import init_cloudinary
from app.db.database import Base, engine
from app.api.pets_router import router
from app.exceptions.pet_exceptions import (
    PetNotFoundError,
    NotPetOwnerError,
    InvalidTokenError,
    ImageUploadError,
)
from app.exceptions.error_handlers import (
    pet_not_found_handler,
    not_pet_owner_handler,
    invalid_token_handler,
    image_upload_handler,
)
from app.messaging.publisher import get_publisher, close_publisher

app = FastAPI(title="Pets Service")

_allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    get_publisher()  # initialize RabbitMQ connection


@app.on_event("shutdown")
def on_shutdown():
    close_publisher()


# ── Register global exception handlers ───────────────────
app.add_exception_handler(PetNotFoundError, pet_not_found_handler)
app.add_exception_handler(NotPetOwnerError, not_pet_owner_handler)
app.add_exception_handler(InvalidTokenError, invalid_token_handler)
app.add_exception_handler(ImageUploadError, image_upload_handler)


# Start cloudinary for image uploading
init_cloudinary()

# ── Include routers ──────────────────────────────────────
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
