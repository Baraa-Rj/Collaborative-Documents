# CLAUDE.md — project plan (survives context resets)

Timed take-home: Ajaia "AI-Native Full Stack Developer Assignment". Brief: ./ASSIGNMENT.md (read it fully).
HARD DEADLINE: submitted by 22:35 Asia/Jerusalem, 2026-11-16. Started ~18:55.
The user owns every decision and must explain all code in a walkthrough video → explain briefly what is built and why.

## Product
Lightweight collaborative doc editor: create/rename/edit/save/reopen rich-text docs (bold, italic, underline, headings,
bullet+numbered lists), import a file as a new doc, share a doc with another user, persistence, deployed live.

## Locked decisions (don't revisit unless broken; if so, tell the user first)
- Backend: FastAPI + SQLAlchemy 2.x + Pydantic. Python venv.
- Frontend: React + Vite + TypeScript + Tiptap. Check installed Tiptap major: v3 StarterKit includes Underline; v2 needs @tiptap/extension-underline.
- One deploy unit: FastAPI serves built frontend (frontend/dist) with SPA fallback; API under /api.
- DB: DATABASE_URL env var. Default sqlite:///./local.db locally; Neon Postgres in prod (normalize postgres:// → postgresql+psycopg://, keep sslmode=require). create_all on startup + idempotent seed. No Alembic (documented cut).
- Deploy: Render free web service via multi-stage Dockerfile (node build → python runtime) + render.yaml. User does dashboard/Neon steps; give exact click-steps.
- Auth: mocked. Seeded users Alice, Bob, Carol (alice@ajaia.test etc.). Frontend user switcher; requests send X-User-Id header. Labeled NOT SECURE in UI + README.
- Content stored as HTML, sanitized server-side with nh3 on every write (stored-XSS risk, docs are shared). Allow only tags the editor produces.
- Import: POST multipart; .txt / .md (markdown lib) / .docx (mammoth) → new doc owned by uploader. 2 MB limit, extension + content validation, clear errors. Supported types stated in UI.
- Sharing: owner shares by email. Shared users can view+edit; only owner can share. Doc list shows "My documents" and "Shared with me" separately, with owner badge.
- Autosave: debounced ~1s with "Saving… / Saved / Error" indicator. Inline title rename.
- Access logic in ONE function get_doc_for_user(doc_id, user_id) used by every endpoint; unauthorized → 404.

## Data model
users(id, name, email unique)
documents(id, owner_id FK, title, content_html, created_at, updated_at)
document_shares(document_id FK, user_id FK, created_at) — composite PK

## API
GET /api/users
GET /api/documents → {owned:[...], shared:[...]}
POST /api/documents
GET /api/documents/{id}
PATCH /api/documents/{id}  (title and/or content_html; title 1–200 chars)
POST /api/documents/import  (multipart)
POST /api/documents/{id}/shares  {email}  (owner only; 400 if self/unknown; idempotent)
GET /api/health

## Explicit cuts (ARCHITECTURE.md, one-line reason each)
Real-time collab, real auth, comments, version history, roles, delete docs, revoke shares, attachments, PDF export, migrations.

## Phases — after EACH: stop, ≤6-line summary + exact verify commands, wait for "next". Commit after each phase.
1. (19:25) Backend: models, seed, all endpoints, sanitization, access check. Runs locally.
2. (19:55) Frontend: user switcher, doc list (owned/shared), editor + toolbar, rename, autosave, error states.
3. (20:20) Dockerfile + render.yaml + FastAPI static serving; Neon + Render steps. Deploy EARLY.
4. (20:55) Import UI + share dialog end to end.
5. (21:15) pytest (TestClient, temp SQLite): Bob 404 on Alice's doc before share, 200 after; non-owner can't share;
   .md import creates formatted doc; <script> stripped on save; bad file type → 400. Redeploy.
   FEATURE FREEZE 21:15. After: docs and fixes only.
6. (21:45) README.md, ARCHITECTURE.md, AI_WORKFLOW.md, SUBMISSION.md, VIDEO_URL.txt placeholder.

## AI workflow log (graded)
Maintain AI_WORKFLOW.md AS WE GO. Real items only: where AI sped things up, AI output changed/rejected and why,
how correctness was verified. Never fabricate entries.

## Rules
- No secrets in git; .env gitignored; .env.example committed. Ask user for keys/URLs.
- No global installs, no sudo without asking.
- Small readable code. No features beyond this plan.
- Blocked >15 min → stop, tell user, propose a cut.

## Status
- SUBMITTED 2026-11-16 20:25 (portal confirmed). Drive folder: https://drive.google.com/drive/folders/1ELkinxPFOP7OcNqW0OzZRJZdArl1V2BO. LIVE: https://ajaia-docs-rcya.onrender.com (Render srv-dbtjqfc9v7es7397shk0, auto-deploys from main). Phase 1-6 done (docs written). FEATURE FREEZE (docs + fixes only). Tests: cd backend && ../.venv/bin/python -m pytest -q (10 tests). Neon project divine-darkness-07907316 linked (secrets in .env.local, gitignored; load with `set -a; . ./.env.local; set +a`). Neon tables+seed created. Branch per phase (phase-N-name), pushed, then ff-merged to main. No Co-Authored-By lines in commits. ASSIGNMENT.md still missing — ask user.
