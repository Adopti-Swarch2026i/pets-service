from fastapi import FastAPI

from sqlalchemy import text
from app.db.database import Base, engine, write_engine
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
from app.messaging.cache_invalidator import start_cache_invalidator, stop_cache_invalidator

app = FastAPI(title="Pets Service")


@app.on_event("startup")
def on_startup():
    with write_engine.connect() as conn:
        conn.execute(text("SELECT pg_advisory_lock(20260601)"))
        try:
            Base.metadata.create_all(bind=write_engine)
        finally:
            conn.execute(text("SELECT pg_advisory_unlock(20260601)"))
    get_publisher()  # initialize RabbitMQ connection
    start_cache_invalidator()


@app.on_event("shutdown")
def on_shutdown():
    stop_cache_invalidator()
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
