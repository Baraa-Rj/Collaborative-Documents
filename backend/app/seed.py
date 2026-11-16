"""Idempotent seed: safe to run on every startup (inserts only missing users)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import User

SEED_USERS = [
    ("Alice", "alice@ajaia.test"),
    ("Bob", "bob@ajaia.test"),
    ("Carol", "carol@ajaia.test"),
]


def seed_users(db: Session) -> None:
    existing = set(db.scalars(select(User.email)))
    for name, email in SEED_USERS:
        if email not in existing:
            db.add(User(name=name, email=email))
    db.commit()
