"""Mocked auth + the single access-control check used by every document endpoint."""
from fastapi import Depends, Header, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .db import get_db
from .models import Document, DocumentShare, User


def get_current_user(
    x_user_id: int | None = Header(default=None), db: Session = Depends(get_db)
) -> User:
    """MOCK AUTH — NOT SECURE. The client just says who it is via the X-User-Id header.
    Real auth (sessions/OIDC) is an explicit cut; see ARCHITECTURE.md."""
    user = db.get(User, x_user_id) if x_user_id is not None else None
    if user is None:
        raise HTTPException(status_code=401, detail="Unknown or missing X-User-Id header.")
    return user


def get_doc_for_user(db: Session, doc_id: int, user_id: int) -> Document:
    """Return the document if the user owns it or it is shared with them.
    Otherwise 404, so a user can't probe which document ids exist."""
    shared_doc_ids = select(DocumentShare.document_id).where(DocumentShare.user_id == user_id)
    doc = db.scalar(
        select(Document).where(
            Document.id == doc_id,
            or_(Document.owner_id == user_id, Document.id.in_(shared_doc_ids)),
        )
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc
