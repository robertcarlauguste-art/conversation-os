# ConversationOS

AI-powered Relationship Intelligence Platform. Not a CRM — an
intelligent layer that sits on top of existing CRMs and automates the
administrative work that happens after client conversations. MVP
customer: Realtors. The architecture is designed to generalize to
insurance, legal, recruiting, and financial advisors without a
rewrite.

**This is Sprint 1: Conversation Intake.** A Realtor can upload an
audio recording, see it appear in a list, and open it to view its
metadata. No AI processing happens yet — this sprint builds the
intake pipeline that transcription, knowledge extraction, and task
generation will plug into in later sprints.

## Stack

- **Frontend:** Next.js 15, React, TypeScript, TailwindCSS, TanStack Query
- **Backend:** Python 3.13, FastAPI, uv, Pydantic v2, SQLAlchemy 2, Alembic
- **Infra:** PostgreSQL 16 + pgvector, Redis, Docker Compose, GitHub Actions

See [`docs/adr/`](./docs/adr) for the reasoning behind these choices,
and [`docs/features/conversation-intake.md`](./docs/features/conversation-intake.md)
for how this sprint's workflow works end to end.

## Setup

### 1. Environment variables

```bash
cp .env.example .env
```

None of the values are required to run this sprint — no AI calls or
auth are implemented yet.

### 2. Run everything with Docker

```bash
docker compose up
```

This launches:

| Service  | URL                         |
|----------|------------------------------|
| Frontend | http://localhost:3000        |
| Backend  | http://localhost:8000        |
| API docs | http://localhost:8000/docs   |
| Postgres | localhost:5432               |
| Redis    | localhost:6379               |

Uploaded files persist in a named Docker volume
(`conversation_storage`), so they survive a container restart.

### 3. Try the demo flow

1. Open http://localhost:3000/conversations.
2. Drag an `.mp3`/`.wav`/`.m4a`/`.aac` file onto the upload zone (or
   click to pick one) — up to 100 MB.
3. Watch the progress bar, then the success notification.
4. The new conversation appears in the table immediately.
5. Click it to see its metadata detail page.

### 4. Verify the API directly

```bash
curl -i http://localhost:8000/health
curl -X POST http://localhost:8000/api/v1/conversations \
  -F "file=@buyer_consultation.mp3;type=audio/mpeg"
curl http://localhost:8000/api/v1/conversations
```

## Local development (without Docker)

### Backend

```bash
cd backend
uv pip install --system -e . ruff black mypy pytest pytest-asyncio httpx
alembic upgrade head
uvicorn app.main:app --reload
```

Run tests / lint:

```bash
pytest
ruff check app tests
black --check app tests
mypy app
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Database migrations

```bash
cd backend
alembic upgrade head
```

Two migrations so far: `0001` enables the `pgvector` extension;
`0002` creates the `conversations` table (the first real business
entity — see [Database schema](#database-schema) below).

## Database schema

**`conversations`**

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| title | String, nullable | Optional |
| filename | String | Original filename |
| storage_path | String | Local storage path (internal — not exposed via API) |
| mime_type | String | Audio MIME type |
| file_size | BigInteger | Bytes |
| duration_seconds | Integer, nullable | Populated in a future sprint |
| status | Enum | `UPLOADED`, `QUEUED`, `PROCESSING`, `COMPLETED`, `FAILED` — only `UPLOADED` used this sprint |
| source | Enum | `UPLOAD`, `PHONE`, `EMAIL`, `IMPORT` — only `UPLOAD` implemented |
| created_at / updated_at | Timestamp | Auto |

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/conversations` | Upload an audio file (multipart `file` field) |
| `GET` | `/api/v1/conversations` | List conversations, newest first |
| `GET` | `/api/v1/conversations/{id}` | Get one conversation's detail |
| `DELETE` | `/api/v1/conversations/{id}` | Delete the record and its stored file |
| `GET` | `/health` | Liveness check |
| `GET` | `/version` | App name/version/env |

Full interactive docs at `/docs` once the backend is running. Every
business response uses `{ "success": bool, "data": ... }`
(`app/schemas/envelope.py`).

## Observability

Every request is logged with a request ID, method, path, status code,
and duration in milliseconds (`app/core/logging.py`), and the same ID
comes back as an `X-Request-ID` response header. Uploads additionally
log `upload_started`, `upload_completed` (or `upload_failed` with the
reason), and the conversation ID — all sharing that request ID, so a
single upload can be traced end to end in the logs. `authenticated_user`
logs as `None` until Clerk auth lands in a future sprint.

## Repository structure

```
conversation-os/
  backend/app/
    api/                 # composition root only (ADR-004) — mounts each slice's router
    core/                 # config, logging, database — centralized (Rule 4)
    shared/                 # domain-agnostic utilities (empty)
    repositories/            # BaseRepository — shared contract (Rule 2)
    services/                 # BaseService — shared contract (Rule 3)
    orchestrator/               # BaseOrchestrator — multi-slice workflow coordination
    providers/                    # AIProvider abstraction (Rule 6) — no vendor calls yet
    models/                         # shared declarative Base only
    schemas/                         # shared response envelope only
    conversation/                     # Sprint 1 vertical slice (see below)
    client/ memory/ communication/
    tasks/ organization/ integrations/ events/   # empty domain packages, future sprints
  backend/tests/                        # cross-cutting tests (health/version)
  backend/alembic/
  frontend/                               # Next.js 15 app router
    src/app/                                  # Dashboard, Conversations, Conversation Detail
    src/components/                             # Nav, UploadDropzone, ConversationsTable, ...
    src/lib/                                      # api client, types, formatting
  docs/
    product/ architecture/ engineering/ adr/ api/ deployment/ features/
  docker-compose.yml
  .github/workflows/       # backend-ci.yml, frontend-ci.yml
```

### The `conversation/` slice (Vertical Slice Architecture, ADR-004)

```
conversation/
  api.py         # thin routes (Rule 1) — mounted by app/api/router.py
  service.py     # business logic (Rule 3), subclasses BaseService
  repository.py  # persistence (Rule 2), subclasses BaseRepository
  models.py      # the Conversation ORM model
  schemas.py     # request/response schemas
  storage.py     # StorageBackend abstraction + LocalStorageBackend
  validators.py  # upload validation rules
  events.py      # ConversationUploaded — no consumers yet
  enums.py       # ConversationStatus, ConversationSource
  tests/         # repository, API, and validator tests
```

Each future slice follows the same shape. See ADR-004 for why this
sits alongside (not instead of) the shared `repositories/`/`services`/
`orchestrator` base classes.

## Architectural rules (see ADR-003, ADR-004 for full rationale)

1. Business logic never lives in API routes — including in the
   composition root, which only mounts slice routers.
2. Database access happens only through repositories
   (`app/repositories/base.py` + each slice's concrete repository).
3. Services contain business logic (`app/services/base.py` + each
   slice's concrete service).
4. Configuration is centralized (`app/core/config.py`).
5. Everything is modular — one slice per business capability;
   workflows spanning multiple slices go through an orchestrator
   (`app/orchestrator/base.py`).
6. AI is abstracted behind `AIProvider` — no direct vendor SDK calls
   from business logic (still unused as of this sprint — no AI calls
   in Sprint 1).

## Next sprint

Sprint 2 adds Transcription, subscribing to the `ConversationUploaded`
event this sprint introduced. Per the working agreement, this build
stops here for review before Sprint 2 begins.
