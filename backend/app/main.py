"""FastAPI app: all /api routes. Every document route resolves the doc through get_doc_for_user()."""
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from .access import get_current_user, get_doc_for_user
from .db import Base, SessionLocal, engine, get_db
from .importers import MAX_IMPORT_BYTES, ImportFailed, file_to_html
from .models import Document, DocumentShare, User, utcnow
from .sanitize import clean_html
from .schemas import DocCreate, DocList, DocOut, DocSummary, DocUpdate, ShareIn, UserOut
from .seed import seed_users


@asynccontextmanager
async def lifespan(app: FastAPI):
    # No migrations (documented cut): create missing tables, then seed users idempotently.
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_users(db)
    yield


app = FastAPI(title="Ajaia Docs", lifespan=lifespan)


def as_utc(dt: datetime) -> datetime:
    # SQLite drops tzinfo; we always store UTC, so re-attach it so clients get an explicit offset.
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def to_summary(doc: Document) -> DocSummary:
    return DocSummary(
        id=doc.id, title=doc.title, owner=UserOut.model_validate(doc.owner), updated_at=as_utc(doc.updated_at)
    )


def to_out(doc: Document, user: User) -> DocOut:
    return DocOut(
        **to_summary(doc).model_dump(),
        content_html=doc.content_html,
        created_at=as_utc(doc.created_at),
        is_owner=doc.owner_id == user.id,
        shared_with=[UserOut.model_validate(s.user) for s in doc.shares],
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    # Unauthenticated on purpose: the mock user switcher needs it before anyone is "logged in".
    return db.scalars(select(User).order_by(User.id)).all()


@app.get("/api/documents", response_model=DocList)
def list_documents(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    owned = db.scalars(
        select(Document).where(Document.owner_id == user.id).order_by(Document.updated_at.desc())
    ).all()
    shared = db.scalars(
        select(Document)
        .join(DocumentShare, DocumentShare.document_id == Document.id)
        .where(DocumentShare.user_id == user.id)
        .order_by(Document.updated_at.desc())
    ).all()
    return DocList(owned=[to_summary(d) for d in owned], shared=[to_summary(d) for d in shared])


@app.post("/api/documents", response_model=DocOut, status_code=201)
def create_document(body: DocCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = Document(owner_id=user.id, title=body.title, content_html=clean_html(body.content_html))
    db.add(doc)
    db.commit()
    return to_out(doc, user)


@app.post("/api/documents/import", response_model=DocOut, status_code=201)
async def import_document(
    file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    data = await file.read(MAX_IMPORT_BYTES + 1)  # read at most limit+1 bytes so huge uploads can't exhaust memory
    try:
        title, html = file_to_html(file.filename or "", data)
    except ImportFailed as e:
        raise HTTPException(status_code=400, detail=str(e))
    doc = Document(owner_id=user.id, title=title, content_html=clean_html(html))
    db.add(doc)
    db.commit()
    return to_out(doc, user)


@app.get("/api/documents/{doc_id}", response_model=DocOut)
def get_document(doc_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return to_out(get_doc_for_user(db, doc_id, user.id), user)


@app.patch("/api/documents/{doc_id}", response_model=DocOut)
def update_document(
    doc_id: int, body: DocUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    doc = get_doc_for_user(db, doc_id, user.id)  # owner and shared users may both edit
    if body.title is not None:
        doc.title = body.title
    if body.content_html is not None:
        doc.content_html = clean_html(body.content_html)
    if body.title is not None or body.content_html is not None:
        doc.updated_at = utcnow()
        db.commit()
    return to_out(doc, user)


@app.post("/api/documents/{doc_id}/shares", response_model=DocOut)
def share_document(
    doc_id: int, body: ShareIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    doc = get_doc_for_user(db, doc_id, user.id)
    if doc.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the owner can share this document.")
    target = db.scalar(select(User).where(User.email == body.email))
    if target is None:
        raise HTTPException(status_code=400, detail=f"No user with email {body.email}.")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="You already own this document.")
    if db.get(DocumentShare, (doc.id, target.id)) is None:  # idempotent: sharing twice is a no-op
        db.add(DocumentShare(document_id=doc.id, user_id=target.id))
        db.commit()
        db.refresh(doc)
    return to_out(doc, user)


# ---- Production: serve the built React app from this same server (one deploy unit, same origin, no CORS).
# Registered last so every /api route above wins. In local dev, Vite serves the UI instead and dist/ may not exist.
FRONTEND_DIST = Path(os.getenv("FRONTEND_DIST", Path(__file__).resolve().parents[2] / "frontend" / "dist")).resolve()

if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")  # unknown API path: JSON 404, not the SPA
        file = (FRONTEND_DIST / path).resolve()
        if path and file.is_file() and file.is_relative_to(FRONTEND_DIST):  # guard against ../ traversal
            return FileResponse(file)
        return FileResponse(FRONTEND_DIST / "index.html")  # SPA fallback
