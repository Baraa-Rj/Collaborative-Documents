# Architecture

## Priorities

With a ~3.5-hour budget, I ranked the work in this order and built it in this order:

1. **Correct access rules.** Sharing is the "collaborative" part. A data leak between users is the worst bug this
   app can have.
2. **Safe shared content.** Documents are HTML that other users open, so stored XSS is a real risk.
3. **Persistence and a live deploy.** The reviewer must be able to use it, refresh, and come back.
4. **Editing UX:** formatting, autosave with clear status, rename, import.
5. Everything else was cut and written down (see [Cuts](#cuts)).

## Overview

```
Browser (React + Tiptap)                      Render (one Docker container)                Neon
┌──────────────────────────┐   same origin    ┌──────────────────────────────────┐        ┌──────────┐
│ User switcher            │  /api/* + JSON   │ FastAPI                          │  SQL   │ Postgres │
│ Doc list (owned/shared)  │ ───────────────▶ │  get_current_user (X-User-Id)    │ ─────▶ │ users    │
│ Editor + autosave        │  X-User-Id hdr   │  get_doc_for_user  → 404         │        │ documents│
│ Import / Share dialog    │ ◀─────────────── │  clean_html (nh3)  on every write│        │ shares   │
└──────────────────────────┘   /assets, SPA   │  importers (.txt/.md/.docx)      │        └──────────┘
                                              │  serves frontend/dist + fallback │
                                              └──────────────────────────────────┘
```

**Data model**
- `users(id, name, email unique)`
- `documents(id, owner_id → users, title, content_html, created_at, updated_at)`
- `document_shares(document_id → documents, user_id → users, created_at)`, with a composite primary key so a user
  can't be added twice

## Key decisions

| Decision | Why |
|---|---|
| **One deploy unit:** FastAPI serves the built React app | One URL, one service, no CORS, and one free Render instance. The SPA route is registered after `/api`, so unknown API paths still return JSON 404s. |
| **Store content as HTML** | Tiptap reads and writes HTML natively, imports (markdown, mammoth) produce HTML, and HTML is easy to inspect. ProseMirror JSON would be more structured but needs converters both ways. |
| **Sanitize on the server, on every write** (nh3 allow-list) | Shared docs make stored XSS a cross-user attack. The allow-list matches what the editor can produce: paragraphs, headings, marks, lists, links with safe schemes. The server never trusts the client. Imports go through the same function. |
| **One access function, `get_doc_for_user`** | Every document route resolves the document through it, so the rule lives in one place. Unauthorized users get **404, not 403**, so they can't probe which ids exist. "Only the owner can share" is checked after access, and returns 403 because the user already knows the doc exists. |
| **Mock auth via `X-User-Id`** | Lets reviewers switch users instantly to test sharing. It's clearly labelled as not secure in the UI and README. Real auth would only change `get_current_user`. |
| **Debounced autosave (~1s) with a serial save queue** | Edits are sent one request at a time, in order, so an older save can't land after a newer one. Failed changes are kept and re-sent. Loading a doc must not trigger a save (see the bug in [AI_WORKFLOW.md](AI_WORKFLOW.md)). |
| **Open doc kept in the URL hash** (`#/doc/5`) | A refresh reopens the same document, and links are shareable, without adding a router library. |
| **SQLite locally, Postgres in prod, same code** | `DATABASE_URL` picks the database. Tests use a throwaway SQLite file and never touch Neon. |
| **`create_all` + idempotent seed on startup** | Zero-step setup for reviewers. It's fine while the schema is new (see Cuts → migrations). |
| **Import validation** | Size is capped by reading at most 2 MB + 1 byte. The extension is checked against an allow-list, and the content is checked too: UTF-8 with no NUL bytes for text, the zip signature for `.docx`. Each failure is a 400 with a human-readable message, and nothing is half-created. |

## Tradeoffs I'm aware of

- **Last write wins.** If two people edit the same document at the same moment, the later autosave overwrites the
  earlier one. That's acceptable for a demo; the fix is in "Next".
- **HTML can be changed by the sanitizer.** Anything outside the allow-list is dropped (for example images from a
  `.docx`). This is safer, but lossy for rich imports.
- **The doc list is refetched after each save**, to keep "last updated" fresh. That's one extra GET per save, which
  is fine at this scale, and there's no pagination.
- **The free tier sleeps**, causing a ~50s cold start. Neon also scales to zero, so the first query after idle is
  slower.

## Cuts

| Cut | Reason |
|---|---|
| Real-time collaboration (cursors, CRDT/OT) | A large subsystem (Yjs + websockets + persistence). Async sharing with autosave covers the brief in the time available. |
| Real authentication | Secure session/OIDC handling takes time and adds nothing to the document features being judged. It's isolated behind `get_current_user`. |
| Comments | A separate feature with its own data model and UI. Not core to editing and sharing. |
| Version history | Needs a snapshots table plus a diff/restore UI. Autosave plus persistence covers "don't lose work". |
| Roles (viewer/commenter/editor) | One "can edit" share level keeps the access rule simple and testable. |
| Deleting documents | Not required for the core flow, and it needs confirmation UX and cascading shares. |
| Revoking shares | Same reasons as deletion. The data model supports it (delete one `document_shares` row). |
| Attachments / images | Needs file storage. Images are stripped by the sanitizer instead of being half-supported. |
| PDF export | Rendering and pagination are a separate problem. Lower value than import for this brief. |
| Migrations (Alembic) | The schema is brand new. `create_all` is enough until the first schema change. |

## Next 2–4 hours

1. **Stop silent overwrites:** add a `version` column, have the client send it with each save, and return `409
   Conflict` when it's stale, with a "this doc changed — reload" banner. About 1 hour.
2. **Revoke a share and delete a document** (owner only), with tests. About 45 minutes.
3. **End-to-end browser tests** (Playwright) for the two-user share flow and autosave/reload, run in CI. About 1 hour.
4. **Alembic baseline migration** before any schema change, plus real auth (e.g. OAuth sign-in replacing
   `X-User-Id`). About 1 hour or more.
