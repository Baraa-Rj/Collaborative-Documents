# Ajaia Docs: a lightweight collaborative document editor

Create, edit and share rich-text documents, import `.txt` / `.md` / `.docx` files, and come back to them later.
Built for the Ajaia "AI-Native Full Stack Developer" assignment.

**Live demo:** https://ajaia-docs-rcya.onrender.com

> **Cold start:** the app runs on Render's free tier, which sleeps after ~15 minutes idle. The first request after
> that can take **~50 seconds**. After that it's fast.

> **Demo login, not secure.** There are no passwords. Pick a seeded user from the "Signed in as" menu, and the browser
> sends that user's id in an `X-User-Id` header. This is a deliberate cut to keep the time on the document features;
> see [ARCHITECTURE.md](ARCHITECTURE.md).

## Seeded users

| Name  | Email              |
|-------|--------------------|
| Alice | `alice@ajaia.test` |
| Bob   | `bob@ajaia.test`   |
| Carol | `carol@ajaia.test` |

## What you can do

- **Create, rename, edit, reopen** documents. The title is edited inline.
- **Format text:** bold, italic, underline, headings (H1–H3), bulleted and numbered lists.
- **Autosave:** changes save about 1 second after you stop typing. The header shows *Saving… / Saved / Error* (with
  *Retry*). Reloading the page reopens the same document.
- **Import a file** as a new document you own:

  | Type    | How it's converted                                       |
  |---------|----------------------------------------------------------|
  | `.txt`  | Blank lines become paragraphs. Text is HTML-escaped.     |
  | `.md`   | Markdown → HTML (headings, emphasis, lists, …)           |
  | `.docx` | Word → HTML via mammoth (headings, bold, italic, lists)  |

  Max **2 MB**. Other types, empty files, binary or non-UTF-8 text, and fake `.docx` files are rejected with a clear
  message.
- **Share** a document with another user by email. Only the **owner** can share. People it's shared with can view
  and edit. The sidebar separates **My documents** from **Shared with me**, and shared docs show an owner badge.

### Two-minute reviewer tour
1. As **Alice**, click **Import file** and pick [`samples/meeting-notes.md`](samples/meeting-notes.md). It opens with
   its formatting.
2. Edit the text and rename the title. Watch *Saving… → Saved*, then reload the page: your changes are there.
3. Click **Share**, enter `bob@ajaia.test`, then **Done**.
4. Switch to **Bob**. The doc is under *Shared with me* with an "Alice" badge. Edit it.
5. Switch to **Carol**. She can't see it. Opening its URL directly shows "Document not found".

## Run locally

Prerequisites: **Python 3.12+** and **Node 22.12+** (or 20.19+). Developed on Python 3.14 / Node 26. The Docker image
uses Python 3.13 / Node 22.

```bash
# 1. Backend (from the repo root)
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements-dev.txt
cd backend
../.venv/bin/uvicorn app.main:app --reload --port 8000     # API on http://localhost:8000/api

# 2. Frontend (second terminal, from the repo root)
cd frontend
npm ci
npm run dev                                               # UI on http://localhost:5173, proxies /api → :8000
```

With no `DATABASE_URL` set, the backend uses a local SQLite file (`backend/local.db`). It creates tables and seeds
the three users on startup, and is safe to restart.

**Production-like, one server:** run `npm run build` in `frontend/`, then start uvicorn as above and open
http://localhost:8000. FastAPI serves the built app and the API from the same origin.

**Docker (the same image Render runs):**
```bash
docker build -t ajaia-docs .
docker run -p 8000:8000 ajaia-docs            # add -e DATABASE_URL=... to use Postgres
```

**Using Postgres (Neon) locally:** put `DATABASE_URL=...` in `.env.local`, which is gitignored (see
[.env.example](.env.example)), and load it before starting the backend: `set -a; . ./.env.local; set +a`.

## Tests

```bash
cd backend
../.venv/bin/python -m pytest -v
```

Ten API tests using FastAPI's TestClient on a throwaway SQLite database, reset before each test. They cover access
control (404 before a share, 200 after), owner-only sharing, share validation, stripping `<script>` and other unsafe
HTML on save, `.md` / `.docx` / `.txt` import, and rejecting bad files. The [AI workflow log](AI_WORKFLOW.md#phase-5-automated-tests-pytest)
describes how the tests themselves were checked, by breaking the code on purpose.

## Deployment

- **Render** free web service, built from the multi-stage [Dockerfile](Dockerfile): Node builds the frontend, and a
  Python image serves both API and UI. Configured by [render.yaml](render.yaml), auto-deploys from `main`, health
  check `GET /api/health`.
- **Neon** serverless Postgres (Frankfurt, same region as Render). The connection string is set as `DATABASE_URL` in
  Render's dashboard and is never committed. `postgres://` URLs are normalised to the psycopg driver, and
  `sslmode=require` is kept.

## Project layout

```
backend/app/
  main.py        routes + serving the built frontend
  access.py      mock auth + get_doc_for_user(): the single access check
  sanitize.py    nh3 allow-list sanitizer, used on every write
  importers.py   .txt/.md/.docx → HTML, with validation
  models.py      users, documents, document_shares
  schemas.py     Pydantic request/response models
  db.py, seed.py
backend/tests/   pytest suite
frontend/src/
  App.tsx        user switcher, layout, URL-hash routing
  DocListPanel.tsx  "My documents" / "Shared with me", import button
  Editor.tsx     Tiptap editor, title rename, debounced autosave
  Toolbar.tsx, ShareDialog.tsx, api.ts
samples/         example files to import
```

## More docs

- [ARCHITECTURE.md](ARCHITECTURE.md): priorities, decisions, tradeoffs, what was cut and why, what's next
- [AI_WORKFLOW.md](AI_WORKFLOW.md): how AI was used, what was changed or rejected, how correctness was verified
- [SUBMISSION.md](SUBMISSION.md): what's included, what works, what's incomplete
