# AI workflow log

Kept as the work happened (not reconstructed at the end). Tool: Claude Code (Claude Opus 5.5) in VS Code.
I set the plan, locked the architecture decisions up front, and reviewed each phase before moving on.

## Phase 1: Backend (FastAPI + SQLAlchemy)

**Where AI sped things up**
- Wrote the plan into CLAUDE.md so it survives context resets, then generated the backend modules
  (db, models, seed, sanitize, importers, access, schemas, main) from the locked decisions in one pass.
- Wrote a throwaway smoke script with FastAPI's TestClient covering every endpoint and error path.

**AI output changed or rejected**
- The smoke run showed SQLite drops timezone info, so `updated_at` came back with no UTC offset
  (the browser would read it as local time). Fixed by re-attaching UTC when serializing (`as_utc` in main.py).

**How correctness was verified**
- Smoke run against a temp SQLite DB. Results:
  - Missing X-User-Id → 401.
  - `<script>`, `onclick`, `<img>` and `javascript:` links were stripped on create and update.
  - Bob got 404 on Alice's doc before the share and 200 after.
  - Re-sharing returned 200 (idempotent). Sharing to an unknown email or to yourself returned 400.
  - Bob (shared, not owner) tried to share → 403. Carol still got 404.
  - A blank title → 422.
  - `.md` import kept the h1, bold, and bullet and numbered lists. `.txt` import escaped HTML.
  - `.pdf`, a fake `.docx`, and a file over 2 MB each → 400 with a clear message.
  - Restarting the app did not duplicate the seeded users.
- Not yet verified: importing a real `.docx` file (planned for Phase 5 tests).

## Phase 2: Frontend (React + Vite + TypeScript + Tiptap v3)

**Where AI sped things up**
- Wrote the Vite/TypeScript scaffold by hand instead of running `create-vite`, whose interactive prompts can hang in a
  non-interactive shell.
- Generated the frontend from the plan:
  - typed API client
  - user switcher
  - owned/shared doc list
  - editor with toolbar, inline title rename, and debounced autosave with a status indicator
- Checked the installed Tiptap version (v3): StarterKit already includes Underline, so no extra package.
- Drove the app in a headless browser (Playwright) to check it end to end instead of only type-checking.

**AI output changed or rejected**
- **Bug found by browser testing:** opening a document triggered an autosave even with no edits, which bumped
  `updated_at` and reordered the doc list. Cause: Tiptap v3's `editor.setEditable(true)` emits an update event by
  default, and the autosave listens for updates. Fix: `setEditable(true, false)`. Verified that a page reload sends
  no PATCH and `updated_at` stays the same.
- The sidebar's "last updated" time was only refreshed after title edits, so it went stale after content edits.
  Now it refreshes after every save.
- Fixed a ProseMirror console warning (`white-space: pre-wrap`) and the missing-favicon 404.
- TypeScript 7 rejected the CSS side-effect import until `vite-env.d.ts` was added.

**How correctness was verified (headless browser + curl against the API)**
- As Alice, created a doc, applied H1, bold and a numbered list, then renamed it. "Saved" appeared, and the server's
  HTML matched what was typed.
- A full page reload reopened the same doc from the URL hash with its formatting intact.
- Bob got 404 on Alice's doc. After sharing it (via API), switching to Bob showed it under "Shared with me" with an
  Alice owner badge. Bob's edit autosaved and is visible to Alice.

## Phase 3: Deploy packaging (Docker + Render)

**Where AI sped things up**
- Generated the multi-stage Dockerfile (Node build → Python runtime, non-root user, `$PORT` from Render),
  `.dockerignore`, `render.yaml`, and FastAPI's static/SPA serving.

**Decisions made while building**
- The SPA catch-all route is registered after all API routes. Unknown `/api/*` paths return a JSON 404 instead of
  `index.html`, so API typos fail loudly.
- Static file lookup resolves the path and checks it stays inside `dist/`, a guard against `../` traversal.
- Render region set to Frankfurt to sit next to the Neon DB (eu-central-1).

**How correctness was verified**
- `docker build` succeeded. Ran the container with `PORT=10000`, mimicking Render, and checked:
  - `/api/health` returns ok and `/api/users` returns the seeded users.
  - `/` and a deep link `/some/route` both return `index.html`.
  - The hashed JS asset is served with the JavaScript content type.
  - `/api/nope` returns a JSON 404.
  - Both traversal attempts (`/../backend/...` and the `%2e%2e` form) got `index.html`, not source files.
