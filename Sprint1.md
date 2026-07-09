# Sprint 1 — Conversation Intake Platform

**Status:** Complete. Demo script verified end-to-end against a real
Postgres database and a running server (not just unit tests — see
Test Summary). Ready for review before Sprint 2.

## 1. Repository Tree

```
conversation-os/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI app assembly
│   │   ├── api/router.py               # composition root (ADR-004)
│   │   ├── api/system.py               # /health, /version
│   │   ├── core/                       # config, logging, database
│   │   ├── repositories/base.py        # BaseRepository (shared)
│   │   ├── services/base.py            # BaseService (shared)
│   │   ├── orchestrator/base.py        # BaseOrchestrator (shared, unused this sprint)
│   │   ├── providers/ai_provider.py    # AIProvider (shared, unused this sprint)
│   │   ├── models/base.py              # shared declarative Base
│   │   ├── schemas/envelope.py         # shared { success, data } response shape
│   │   └── conversation/               # Sprint 1 vertical slice
│   │       ├── api.py            service.py       repository.py
│   │       ├── models.py         schemas.py        storage.py
│   │       ├── validators.py     events.py          enums.py
│   │       └── tests/
│   │           test_api.py  test_repository.py  test_validators.py  conftest.py
│   ├── alembic/versions/
│   │   ├── 0001_initial_baseline.py         # pgvector extension (Sprint 0)
│   │   └── 0002_create_conversations_table.py
│   └── tests/                          # cross-cutting: health/version/request-id
├── frontend/src/
│   ├── app/
│   │   ├── page.tsx                    # Dashboard
│   │   ├── conversations/page.tsx      # Conversations list + upload
│   │   ├── conversations/[id]/page.tsx # Conversation detail
│   │   ├── layout.tsx, providers.tsx
│   ├── components/
│   │   ├── Nav.tsx  UploadDropzone.tsx  ConversationsTable.tsx
│   │   ├── SummaryCards.tsx  StatusBadge.tsx  Toast.tsx  WaveformMark.tsx
│   └── lib/
│       ├── api.ts (fetch/XHR client)  types.ts  format.ts
├── docs/
│   ├── adr/004-vertical-slice-architecture.md   (new)
│   ├── adr/002-repository-structure.md          (updated — partially superseded)
│   ├── features/conversation-intake.md          (new)
│   ├── api/README.md, architecture/README.md    (updated)
├── docker-compose.yml                  # + conversation_storage volume
└── .github/workflows/backend-ci.yml    # + alembic upgrade step
```

## 2. Database Schema

See the root `README.md` → Database Schema section for the full
`conversations` table. Two migrations exist: `0001` (pgvector
extension, Sprint 0) and `0002` (the `conversations` table, this
sprint). Verified against a real local Postgres instance — not just
reviewed as SQL.

## 3. API Documentation

See `docs/api/README.md` and the live `/docs` Swagger UI. Summary:
`POST/GET/GET-by-id/DELETE` on `/api/v1/conversations`, plus
`/health` and `/version`.

## 4. Screenshots of UI

**Not included as image files** — this sandbox has no headless
browser and no network access to download one (the environment's
allowlisted domains cover package registries, not browser binaries),
so I can't render and capture the actual pages here. What I can
confirm instead: `next build` succeeded, all 4 routes compiled
(`/`, `/conversations`, `/conversations/[id]`, `/_not-found`), and
`eslint`/`tsc --noEmit` are clean. If you'd like real screenshots,
running `docker compose up` and visiting `localhost:3000` takes about
30 seconds, or I can drive it live via a connected browser tool if
you'd rather I capture them for you.

**UI summary:**
- **Dashboard** (`/`) — five summary cards (Total, Uploaded,
  Processing, Completed, Failed), counts derived client-side from the
  conversation list per spec ("mock values acceptable" — these aren't
  mocked, just client-computed since there's no aggregation endpoint
  yet).
- **Conversations** (`/conversations`) — drag-and-drop/file-picker
  upload zone with a live progress bar, then the table (Title,
  Status, Uploaded, File Size, Actions) below it.
- **Conversation Detail** (`/conversations/{id}`) — metadata fields
  plus the three placeholder cards (Transcript / Knowledge / Tasks)
  exactly as specified, each labeled with the sprint that fills it in.

Design direction: warm paper background, a serif display face for
headings, a teal accent (not the generic AI-tool purple/clay), and a
small waveform mark as the one recurring signature element, used in
the nav, upload zone, and empty states.

## 5. Test Summary

**15/15 backend tests passing**, run against a real local Postgres 16
instance (installed in this sandbox specifically to verify against,
not mocked):

- `tests/test_system.py` (3) — health, version, 404 + request-id.
- `app/conversation/tests/test_validators.py` (5) — accepted format,
  rejected extension, oversized file, empty file, mismatched MIME type.
- `app/conversation/tests/test_repository.py` (4) — add/get, sort
  order, missing-record lookup, delete.
- `app/conversation/tests/test_api.py` (3) — full upload→list→get→delete
  round trip, rejected file type at the API layer, 404 on unknown id.

`ruff`, `black --check`, and `mypy` all clean across the backend.
Frontend: `eslint`, `tsc --noEmit`, and `next build` all pass.

**Beyond automated tests**, the full demo script from the spec was
run against a live `uvicorn` server with `curl`: upload a fake
`buyer_consultation.mp3` → appears in the list → detail page shows
correct metadata → invalid file type correctly rejected with a
`422` → delete → subsequent `GET` correctly `404`s. Server logs
confirmed `upload_started` / `upload_completed` / `upload_failed`
all carry the same `request_id` as the surrounding request log line.

## 6. Architecture Summary

See `docs/architecture/README.md`. Short version: shared, logic-free
infrastructure (`core`, `repositories`, `services`, `orchestrator`,
`providers`, `models`, `schemas`) plus vertical slices per business
capability (`conversation/` is the first). `app/api/router.py` is a
composition root, not a route file. Full reasoning, including the
architectural conflict this sprint surfaced and how it was resolved,
is in [ADR-004](./docs/adr/004-vertical-slice-architecture.md).

## 7. Risks Identified

- **`app/events/` is now a stale stub.** Sprint 0 created it as a
  top-level domain package; ADR-004 moved domain events into each
  slice's own `events.py` instead. The folder still exists, empty —
  worth deleting or repurposing as a shared event-bus location in
  Sprint 2 rather than leaving it ambiguous.
- **`storage.py` lives inside `conversation/`** even though file
  storage is a generic concern. Fine with one slice; if a second
  slice needs storage, duplicate logic is a real risk — flagged in
  ADR-004 to move it to shared infrastructure at that point, not
  before (avoiding speculative abstraction now).
- **No screenshots** for this deliverable, per the sandbox limitation
  above — the UI itself is verified via a real production build, not
  a screenshot, but that's a different kind of verification than
  visual review.
- **Git workflow wasn't simulated.** The spec's feature-branch naming
  (`feature/COS-011-...`) is a convention for your actual repository
  — I didn't fabricate git history in this sandbox, since a synthetic
  commit log would be misleading rather than useful. Apply the branch
  names when you push this to your real remote.
- **`duration_seconds` is always null this sprint** — no audio
  metadata extraction happens yet (explicitly out of scope). The
  column and UI field exist and render `—` correctly; populating it
  is Sprint 2+ work once transcription touches the file.

## 8. Recommendations for Sprint 2

1. Resolve the `app/events/` stub (delete, or repurpose as the home
   for a shared event bus once Transcription needs to subscribe to
   `ConversationUploaded`).
2. Decide where transcription output lives: a new `transcript.py`
   inside `conversation/`, or a new `transcription/` slice that
   depends on `conversation/`. Worth an ADR given the pipeline
   direction the CTO note established.
3. Add a real backend aggregation endpoint for the Dashboard's summary
   counts once conversation volume makes client-side counting
   wasteful (fine at current scale).
4. If audio duration extraction is trivial to add alongside storage
   (e.g. via a lightweight metadata read at upload time), consider
   pulling it into Sprint 2 rather than deferring further — it's a
   small addition to `service.py`'s `upload()` method and closes a
   currently-empty field.
