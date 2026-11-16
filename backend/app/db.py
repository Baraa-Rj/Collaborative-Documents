"""Database engine/session setup. DATABASE_URL picks SQLite locally or Neon Postgres in prod."""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def normalize_db_url(url: str) -> str:
    """Neon/Render hand out postgres:// URLs; SQLAlchemy needs an explicit driver (psycopg 3).
    Query params such as sslmode=require are kept as-is."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


DATABASE_URL = normalize_db_url(os.getenv("DATABASE_URL", "sqlite:///./local.db"))

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
# pool_pre_ping: Neon suspends idle computes, so stale pooled connections get replaced instead of erroring.
engine = create_engine(DATABASE_URL, connect_args=_connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: one session per request, always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
