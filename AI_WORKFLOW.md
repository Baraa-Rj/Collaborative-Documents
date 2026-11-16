# AI workflow log

Kept as the work happened (not reconstructed at the end). Tool: Claude Code (Claude Opus 5.5) in VS Code.
I set the plan, locked the architecture decisions up front, and reviewed each phase before moving on.

## Summary

- **How I worked:** I wrote the plan, stack, data model, API, and an explicit cut list *before* any code, and put
  them in `CLAUDE.md` so the agent kept to them across context resets. The work ran in six phases. Each ended with a
  summary, verify commands, and a commit on its own branch, merged to `main`. Render auto-deploys from `main`.
- **Where AI helped most:** writing boilerplate fast (FastAPI routes, Pydantic schemas, Tiptap toolbar, Dockerfile),
  writing tests, and *driving a real browser* (Playwright) to catch bugs a type-checker can't.
- **Bugs caught by verification, not by reading code:**
  - Opening a doc triggered an autosave.
  - SQLite returned timestamps without a timezone.
  - `.txt` imports left a trailing `<br>`.
  - The Render deploy failed because of a wrong `DATABASE_URL`.
- **AI output I rejected or changed:**
  - Global CLI installs (ran via `npx` instead).
  - Neon's default `neon.ts` + npm config in a Python project (skipped).
  - A too-realistic example password that caused a failed deploy (lesson recorded below).
- **How correctness was checked:**
  - 10 pytest tests, themselves checked by breaking the code on purpose.
  - Headless-browser runs of the two-user share flow and reload-persistence.
  - Smoke tests of the Docker image and the live URL.

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

## Neon setup (between Phases 3 and 4)

**Where AI sped things up**
- Followed Neon's agent instructions (`neon.com/get-started/prompt.md` and the `neon` SKILL.md) to link the existing
  project and populate env vars with `neon init`.

**AI output changed or rejected**
- Neon's instructions say `npm i -g neon`. Rejected because of my "no global installs" rule; ran the CLI with
  `npx neon@latest` instead.
- `neon init -y` creates a `neon.ts` file and installs npm config dependencies by default. Skipped with `--no-config`,
  because the backend is Python and doesn't use them.
- Didn't run `neon mcp` or `neon skills` separately. The Neon skill says not to when `init` already installed the
  plugin, and the plugin already ships all the skills plus an OAuth MCP server, so a second install would duplicate them.

**How correctness was verified**
- Checked that `.env.local` (secrets) and `.neon` are gitignored before committing. `neon init` added them itself.
- Ran the backend against Neon:
  - The driver resolves to `postgresql+psycopg` and the Neon URL works with `sslmode` and `channel_binding` as-is.
  - Tables were created and the users seeded. A second startup didn't duplicate them.
  - Authenticated reads return 200.
  - A Document insert succeeded inside a transaction that was then rolled back, so no test data was left behind.

## Deploy to Render (Phase 3, finished)

**What happened**
- The first two Render deploys failed at startup with "password authentication failed": the `DATABASE_URL` pasted into
  Render didn't match the working one. The first had the wrong user, the second the wrong password.
- My mistake (AI): to explain the URL format, I gave an example URL with a made-up `npg_…` password of the same length
  as the real one. That example likely ended up in Render. Lesson: placeholders should look obviously fake, e.g.
  `<PASSWORD>`.
- The diagnosis didn't rely on guessing:
  - The same Docker image ran locally against Neon with `.env.local` and started fine, so the code was ruled out.
  - Render's runtime logs (read through Playwright after I logged in myself) showed the exact failing database user.
  - A direct psycopg connection proved the `.env.local` password was still valid.
- I entered the secret into Render's dashboard myself. The AI cleared and focused the field but won't type credentials.

**How correctness was verified (live URL)**
- `/api/health` returns ok and `/api/users` returns the 3 seeded users from Neon.
- No X-User-Id → 401. An unknown `/api` path returns a JSON 404.
- `/` and a deep link return the SPA, and the hashed asset returns 200.
- In a real browser, the UI loads with the user switcher, "My documents" / "Shared with me", and no console errors.

## Phase 4: Import UI + share dialog

**Where AI sped things up**
- Built the "Import file" button (with supported types and the 2 MB limit shown under it), a client-side size
  pre-check, and an owner-only Share dialog with error states and a "Who has access" list.
- Generated a real minimal `.docx` (OOXML zip with heading styles) plus `.md`/`.txt` samples in `samples/`, so import
  could be tested for real and reviewers have files to try.

**AI output changed or rejected**
- **Found in browser testing:** a `.txt` file ending in a newline left a stray `<br>` at the end of the last
  paragraph. Fixed by trimming newlines from each paragraph in `importers.py`.
- **Test mistake (AI's, not the app's):** my first share test assumed Alice was signed in, but the test browser
  remembered Bob from earlier. The app's 400 "You already own this document" was correct. Re-ran the checks with the
  right user.

**How correctness was verified (browser + API, local)**
- `.md` → H1/H2, bold, italic, bullet and numbered lists preserved.
- `.docx` → headings, bold, italic preserved.
- `.txt` → paragraphs kept and `<b>` shown as literal text.
- `.pdf` → "Import failed: Unsupported file type" banner, no doc created.
- Share dialog: unknown email → 400 message. Sharing with yourself → 400. A valid share updates "Who has access",
  and the email is matched case-insensitively.
- As the recipient: the doc appears under "Shared with me" with an owner badge and no Share button, and their edit
  autosaved and is visible to the owner.
- The third user gets 404. The recipient trying to share via the API gets 403.

## Phase 5: Automated tests (pytest)

**Where AI sped things up**
- Wrote `backend/tests/` (10 tests) with FastAPI TestClient against a throwaway SQLite file. Every test gets a fresh,
  re-seeded database.
- Covered:
  - Bob gets 404 before the share and 200 after, and Carol stays 404.
  - A non-owner can't share (403). A user with no access gets 404.
  - Share validation: unknown email or yourself → 400, re-sharing creates no duplicate.
  - `<script>`, event handlers, `<img>` and `javascript:` links are stripped on both create and update.
  - Title validation.
  - `.md` and `.docx` imports keep their formatting, and `.txt` imports are escaped.
  - Bad files (pdf, no extension, fake docx, binary, non-UTF-8, empty, >2 MB) → 400 with nothing created.

**How the tests themselves were verified (mutation check)**
- Disabled the sanitizer (`clean_html` returned its input unchanged) → the XSS test failed.
- Made `get_doc_for_user` ignore the user → the access and owner-only-share tests failed.
- Restored the code (`git checkout`) → 10/10 pass. The tests fail when the rules they guard are broken.

## Phase 6: Documentation

**Where AI sped things up**
- Drafted README, ARCHITECTURE, and SUBMISSION from the plan in `CLAUDE.md`, the commit history, and this log.

**How the docs were checked**
- Commands were checked against reality before being written down:
  - FastAPI serves the built frontend on :8000 (`/` and a deep link both return the app).
  - The test command runs 10 tests, and the Docker image runs.
  - The live URL works.
- The file list in SUBMISSION.md was generated from `git ls-files`, not typed by hand.
- Every statement about behaviour points to something verified above. Where something wasn't verified, the docs say
  so (see SUBMISSION.md → "Not verified").

## Manual check on the live site (done by me, 2026-11-16, ~19:55)

Done in a normal browser on https://ajaia-docs-rcya.onrender.com, following the README tour. All steps worked:
- **Alice:** imported `samples/meeting-notes.md`, and the formatting was preserved. Edited and renamed the doc, saw
  *Saving… → Saved*, and after a page refresh the edit and title were still there.
- **Alice:** shared the doc with `bob@ajaia.test`, and Bob appeared under "Who has access".
- **Bob:** the doc showed under "Shared with me" with an Alice badge and no Share button. Bob's edit saved and was
  visible to Alice.
- **Carol:** saw no documents. Opening the doc's URL directly showed "Document not found, or you don't have access
  to it."

## Walkthrough video: AI-recorded and AI-narrated (disclosed)

- **I asked Claude to record and narrate the walkthrough.** The video says so on its opening card, says so aloud, and
  shows an "AI-narrated walkthrough" badge throughout. The voice is a stock synthetic voice (Microsoft Edge TTS
  `en-US-GuyNeural` via the `edge-tts` package), not a clone of my voice, and it refers to me in the third person.
- **How it was made:**
  - A scripted Playwright session against the live URL showed every feature:
    - create, rename and format
    - autosave and reload
    - `.docx` import and `.pdf` rejection
    - sharing with validation
    - Bob editing, and Carol getting a 404
  - Slides were generated from the real repo files: the `access.py`, `sanitize.py` and `Editor.tsx` excerpts, real
    `pytest -v` output, and the cuts table from ARCHITECTURE.md.
  - Each narration clip was placed at the recorded start time of its section, and A/V sync was checked frame by frame.
- **Also a production run:** recording it was one more end-to-end pass on the live site, and every scripted step
  passed.
- **An earlier silent 70-second capture** had a screen-capture glitch (a grey band for about 9 seconds). That glitch
  didn't recur in the final recording.
- **Ownership:** the scope decisions, the plan in CLAUDE.md, and the review of each phase are mine. I'm accountable
  for everything the narration says, and I can explain any part of the code.
