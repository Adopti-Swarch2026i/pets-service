from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_REPLICA_URL = os.getenv("DATABASE_REPLICA_URL", DATABASE_URL)

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Master: escrituras (INSERT/UPDATE/DELETE)
write_engine = create_engine(DATABASE_URL, pool_pre_ping=True)
WriteSession = sessionmaker(autocommit=False, autoflush=False, bind=write_engine)

# Replica: lecturas (SELECT) — fallback al master si no hay replica configurada
read_engine = create_engine(DATABASE_REPLICA_URL, pool_pre_ping=True)
ReadSession = sessionmaker(autocommit=False, autoflush=False, bind=read_engine)

Base = declarative_base()

# Alias de compatibilidad — el código existente usa SessionLocal, get_db() y engine
SessionLocal = WriteSession
engine = write_engine


def get_db():
    """Dependency for FastAPI routes — yields a WRITE DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_read_db():
    """Dependency for FastAPI routes — yields a READ-ONLY DB session (replica)."""
    db = ReadSession()
    try:
        yield db
    finally:
        db.close()
