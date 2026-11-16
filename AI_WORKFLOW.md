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
