from fastapi import FastAPI
from .database import Base, engine
from .routes import router

app = FastAPI(title="Pets Service")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
