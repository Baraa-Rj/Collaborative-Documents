# Submission

- **Live app:** https://ajaia-docs-rcya.onrender.com (free tier: the first load after idle can take ~50s)
- **Repository:** https://github.com/Baraa-Rj/Collaborative-Documents (`main` is the submitted version; each build
  phase also has its own `phase-N-*` branch)
- **Walkthrough video:** see [VIDEO_URL.txt](VIDEO_URL.txt)
- **Demo users:** Alice / Bob / Carol (`alice@ajaia.test`, `bob@ajaia.test`, `carol@ajaia.test`), chosen in the
  "Signed in as" menu. No passwords. This is mock auth, not secure, as stated in the UI and README.

## Google Drive folder contents

| File | What it is |
|---|---|
| `source-code.zip` | The full repository at the submitted commit (everything listed under "Files included" below) |
| `README.md` | Local setup, run and test instructions, live URL, seeded users, supported file types |
| `ARCHITECTURE.md` | Architecture note: priorities, decisions, tradeoffs, cuts, next 2–4 hours |
| `AI_WORKFLOW.md` | AI workflow note: tools used, where AI helped, what was changed or rejected, how it was verified |
| `SUBMISSION.md` | This file |
| `LIVE_URL.txt` | The live product URL |
| `VIDEO_URL.txt` | The walkthrough video URL |

No screenshots are included: setup needs no extra steps beyond the README, and the live URL needs no account.

## What works

- Create, rename (inline), edit, and reopen rich-text documents: bold, italic, underline, H1–H3, bulleted and
  numbered lists.
- Debounced autosave (~1s) with a *Saving… / Saved / Error + Retry* indicator. Content and title persist across
  reloads and restarts (Neon Postgres in production).
- Import `.txt`, `.md` and `.docx` (max 2 MB) as a new document owned by the uploader. Supported types are shown in
  the UI, and unsupported or invalid files get a clear error.
- Share by email (owner only). People it's shared with can view and edit. The sidebar shows "My documents" and
  "Shared with me" separately, with an owner badge.
- Access control in one function: no access gives 404, a non-owner sharing gives 403. HTML is sanitized on the server
  on every write.
- 10 automated API tests (`cd backend && ../.venv/bin/python -m pytest -v`).
- One-container deploy (Docker on Render) with Neon Postgres. Auto-deploys from `main`.

## Incomplete / deliberately cut

Each cut has a one-line reason in [ARCHITECTURE.md → Cuts](ARCHITECTURE.md#cuts): real-time co-editing, real
authentication, comments, version history, share roles, deleting documents, revoking shares, attachments/images,
PDF export, and migrations.

Known limitations:
- Concurrent edits to the same document are last-write-wins.
- Images inside `.docx` files are dropped by the sanitizer.
- No frontend unit or end-to-end test suite. The UI was checked by scripted headless-browser runs during development
  (see AI_WORKFLOW.md).

## Not verified

- Imports were tested with the generated sample `.docx` in `samples/`, not with a wide range of real Word files.
- The UI was exercised in Chromium (scripted) and in my own browser on the live site (manual two-user check, see AI_WORKFLOW.md). Other browsers and mobile layouts weren't tested.

## Next steps

See [ARCHITECTURE.md → Next 2–4 hours](ARCHITECTURE.md#next-24-hours):
1. Version-checked saves (409 on a stale save) to stop silent overwrites.
2. Revoking shares and deleting documents.
3. Playwright end-to-end tests in CI.
4. Alembic and real auth.

## Files included

Generated from `git ls-files`.

**Docs**
- `README.md`: setup, run, test, live URL, seeded users, supported file types
- `ARCHITECTURE.md`: priorities, decisions, tradeoffs, cuts, next steps
- `AI_WORKFLOW.md`: how AI was used, what was changed or rejected, how correctness was verified
- `SUBMISSION.md`: this file
- `VIDEO_URL.txt`: link to the walkthrough video
- `LIVE_URL.txt`: link to the live app
- `CLAUDE.md`: the plan and rules given to the AI coding agent (kept as evidence of the workflow)

**Backend (FastAPI)**
- `backend/app/__init__.py`, `main.py`, `access.py`, `sanitize.py`, `importers.py`, `models.py`, `schemas.py`,
  `db.py`, `seed.py`
- `backend/tests/conftest.py`, `backend/tests/test_api.py`, `backend/pytest.ini`
- `backend/requirements.txt`, `backend/requirements-dev.txt`

**Frontend (React + Vite + Tiptap)**
- `frontend/src/App.tsx`, `DocListPanel.tsx`, `Editor.tsx`, `Toolbar.tsx`, `ShareDialog.tsx`, `api.ts`, `main.tsx`,
  `styles.css`, `vite-env.d.ts`
- `frontend/index.html`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/tsconfig.json`,
  `frontend/vite.config.ts`

**Deploy and config**
- `Dockerfile`, `.dockerignore`, `render.yaml`, `.env.example`, `.gitignore`

**Sample files to import**
- `samples/meeting-notes.md`, `samples/plain-notes.txt`, `samples/project-brief.docx`

Not included: secrets (`.env.local` is gitignored; `DATABASE_URL` lives only in Render's dashboard), `node_modules`,
build output, and local databases.
