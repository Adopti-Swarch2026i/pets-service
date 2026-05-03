from fastapi import FastAPI

from app.db.database import Base, engine
from app.api.pets_router import router
from app.exceptions.pet_exceptions import (
    PetNotFoundError,
    NotPetOwnerError,
    InvalidTokenError,
)
from app.exceptions.error_handlers import (
    pet_not_found_handler,
    not_pet_owner_handler,
    invalid_token_handler,
)
from app.messaging.publisher import get_publisher, close_publisher

app = FastAPI(title="Pets Service")


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


# ── Include routers ──────────────────────────────────────
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
