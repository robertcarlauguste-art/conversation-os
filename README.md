# ConversationOS

AI-powered Relationship Intelligence Platform. Not a CRM — an
intelligent layer that sits on top of existing CRMs and automates the
administrative work that happens after client conversations. MVP
customer: Realtors. The architecture is designed to generalize to
insurance, legal, recruiting, and financial advisors without a
rewrite.

**Sprint 4: Executive Command Center is complete.** The dashboard now combines
conversation health, client follow-ups, explainable contact recommendations,
open commitments, recent activity, and an on-demand AI morning briefing in one
operational view. Follow-up actions and task completion are durable and
auditable. See [`Sprint4.md`](./Sprint4.md) for the implementation and rules.

## Stack

- **Frontend:** Next.js 16, React, TypeScript, TailwindCSS, TanStack Query
- **Backend:** Python 3.13, FastAPI, uv, Pydantic v2, SQLAlchemy 2, Alembic
- **AI:** Anthropic Claude (extraction), OpenAI Whisper (transcription)
- **Infra:** PostgreSQL 16 + pgvector, Redis, Docker Compose, GitHub Actions

See [`docs/adr/`](./docs/adr) for the reasoning behind these choices.

## Setup

### 1. Environment variables

```bash
cp .env.example .env
```

**This sprint requires two API keys** to see the full pipeline run —
without them, uploads still succeed but processing fails gracefully
(conversation status becomes `FAILED` rather than the request
erroring):

```bash
ANTHROPIC_API_KEY=sk-ant-...   # https://console.anthropic.com
OPENAI_API_KEY=sk-...          # https://platform.openai.com — used for Whisper transcription only
```

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
3. Watch the progress bar, then the success notification. Processing
   (transcription + extraction) runs synchronously as part of the
   upload this sprint — see TD-003 in `Sprint2.md`.
4. The new conversation appears in the table with its final status
   (`COMPLETED` or `FAILED`).
5. Click it to see Summary, Decisions, Action Items, People, Topics,
   and the transcript (collapsible).

### 4. Verify the API directly

```bash
curl -i http://localhost:8000/health
curl -X POST http://localhost:8000/api/v1/conversations \
  -F "file=@buyer_consultation.mp3;type=audio/mpeg"
curl http://localhost:8000/api/v1/memories/by-conversation/<conversation_id>
```

## Local development (without Docker)

### Backend

```bash
cd backend
uv pip install --system -e . ruff black mypy pytest pytest-asyncio types-aiofiles
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

Tests never call real AI vendors — they use `tests/fakes.py`'s
`FakeAIProvider`/`FakeTranscriptionProvider`, injected via
`monkeypatch`. No API keys are needed to run the test suite.

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

The migration chain now runs through Sprint 4: `0001` enables `pgvector`;
`0002` creates conversations; `0003` creates extracted-memory tables; `0004`
adds clients and client facts; `31c729384386` expands structured memory
entities; `0005` adds durable follow-up history; and `0006` adds action-item
completion timestamps. Run `alembic upgrade head` before starting the backend.

## Database schema

**`conversations`** (Sprint 1) — see previous schema; `status` now
actively uses `UPLOADED` → `PROCESSING` → `COMPLETED`/`FAILED` this
sprint (only `UPLOADED` was used in Sprint 1). `+ client_id` (nullable
FK, this sprint).

**`transcripts`** — one per conversation:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| conversation_id | UUID | FK → conversations, unique, cascade delete |
| text | Text, nullable | The transcribed text |
| language | String, nullable | Detected language code |
| status | Enum | `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED` |
| error_message | Text, nullable | Set when status is `FAILED` |
| created_at / updated_at | Timestamp | Auto |

**`memories`** — one per conversation:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| conversation_id | UUID | FK → conversations, unique, cascade delete |
| title | String, nullable | Not populated yet |
| summary | Text | Required |
| memory_type | Enum | Only `CONVERSATION_SUMMARY` used this sprint |
| topics | String array | Flat list, no separate table (see Sprint2.md) |
| confidence | Float | 0.0–1.0, from the LLM |
| source | String | Model name that produced this memory |
| created_at / updated_at | Timestamp | Auto |

**`decisions`** / **`action_items`** / **`people`** — child tables of
`memories` (FK `memory_id`, cascade delete): `description` (Text) for
decisions/action items, plus `owner` (nullable) on action items;
`name` + `role` (nullable) on people. `people` gains `+ client_id`
(nullable FK) this sprint.

**`clients`** (this sprint) — durable identity independent of any one
conversation:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| full_name | String | Required |
| email / phone | String, nullable | Not populated by extraction yet |
| role | String, nullable | Last-reconciled role — see ADR-005 |
| created_at / updated_at | Timestamp | Auto |

**`client_facts`** (this sprint) — provenance is required, not
optional (FD-005): `client_id` (FK, cascade delete), `fact_text`,
`source_conversation_id` and `source_memory_id` (both FK, cascade
delete, **not nullable**), `confidence` (nullable), `created_at`
(the extraction timestamp).

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/conversations` | Upload audio; now also runs the full processing pipeline |
| `GET` | `/api/v1/conversations` | List conversations, newest first |
| `GET` | `/api/v1/conversations/{id}` | Get one conversation's detail |
| `DELETE` | `/api/v1/conversations/{id}` | Delete the record and its stored file |
| `GET` | `/api/v1/transcriptions/by-conversation/{id}` | Get the transcript for a conversation |
| `GET` | `/api/v1/memories` | List all memories, newest first |
| `GET` | `/api/v1/memories/{id}` | Get one memory by its own id |
| `GET` | `/api/v1/memories/by-conversation/{id}` | Get the memory for a conversation |
| `GET` | `/api/v1/clients` | List clients, most recently updated first |
| `GET` | `/api/v1/clients/{id}` | Client profile with remembered facts |
| `GET` | `/api/v1/clients/{id}/conversations` | Conversations linked to a client |
| `POST` | `/api/v1/clients/{client_id}/conversations/{conversation_id}` | Manually link (correcting a match) |
| `DELETE` | `/api/v1/clients/{client_id}/conversations/{conversation_id}` | Manually unlink |
| `GET` | `/api/v1/dashboard` | Unified command-center payload |
| `POST` | `/api/v1/dashboard/briefing` | Generate an on-demand AI morning briefing |
| `POST` | `/api/v1/dashboard/recommendations/{client_id}/actions` | Record, snooze, or complete a follow-up recommendation |
| `POST` | `/api/v1/memories/action-items/{action_item_id}/complete` | Complete an extracted action item |
| `POST` | `/api/v1/memories/action-items/{action_item_id}/reopen` | Reopen a completed action item |
| `GET` | `/health` / `/version` | Operational endpoints |

Full interactive docs at `/docs`. Every business response uses
`{ "success": bool, "data": ... }` (`app/schemas/envelope.py`).

## Observability

Unchanged from Sprint 1 (request ID, method, path, status, duration,
`X-Request-ID` header) — plus structured log lines from the pipeline,
now including `event=ClientCreated`/`ClientMatched`/
`ClientProfileUpdated`, sharing the request ID of the upload that
triggered them.

## Repository structure

```
conversation-os/
  backend/app/
    api/                 # composition root only (ADR-004) — mounts each slice's router
    core/                 # config, logging, database — centralized (Rule 4)
    repositories/            # BaseRepository — shared contract (Rule 2)
    services/                 # BaseService — shared contract (Rule 3)
    orchestrator/               # BaseOrchestrator + concrete orchestrator
      base.py
      conversation_processing.py   # coordinates conversation+transcription+memory+client
      dependencies.py               # assembles it from the four services
    providers/                        # AI/transcription abstractions (Rule 6)
      ai_provider.py claude_provider.py
      transcription_provider.py openai_whisper_provider.py
      dependencies.py
    models/ schemas/                        # shared Base + response envelope only
    conversation/                             # + client_id, update_client (Sprint 3)
    transcription/                              # audio to text
    memory/                                        # text to structured knowledge; + people.client_id
    client/                                          # NEW slice — durable client identity + facts
    communication/ tasks/ organization/
    integrations/                                       # empty domain packages, future sprints
  backend/tests/                        # cross-cutting tests + shared fakes.py
  backend/alembic/
  frontend/
    src/app/                # Dashboard, Conversations, Conversation Detail, Clients
    src/components/            # + ClientsTable, ClientField (Sprint 3)
    src/lib/                      # api client, types, formatting
  docs/adr/ features/ ...
  docker-compose.yml
  .github/workflows/
```

Note: `app/events/` (the Sprint 0 stub, TD-002) was removed this
sprint per FD-004 — zero references confirmed, full suite re-verified
green afterward.

### New slice this sprint

```
client/
  models.py  schemas.py  repository.py
  service.py  validators.py  events.py  api.py  tests/
```

Same shape as `conversation/`/`transcription/`/`memory/` (ADR-004).
See `Sprint3.md` for the full reconciliation pipeline.

## Architectural rules (see ADR-002, ADR-003, ADR-004, ADR-005)

1. Business logic never lives in API routes.
2. Database access happens only through repositories.
3. Services contain business logic.
4. Configuration is centralized (`app/core/config.py`).
5. Everything is modular — one slice per business capability;
   workflows spanning multiple slices go through an orchestrator.
6. AI is abstracted behind `AIProvider`/`TranscriptionProvider` — no
   direct vendor SDK calls from business logic. No new abstraction
   needed this sprint — client matching (ADR-005) is deterministic,
   not AI-based.

## Technical debt (tracked, see Sprint3.md for full detail)

- **TD-001**: `storage.py` still lives in `conversation/`. Re-evaluated
  this sprint per the Engineering Guide's own threshold (two-slice
  trigger) — `client/` didn't need storage, so still only one
  dependent. Left as-is.
- **TD-002**: resolved this sprint (FD-004).
- **TD-003**: upload processing runs synchronously inside the
  request. Deliberate simplicity tradeoff — revisit once latency or
  retry needs make it user-visible.
- **TD-004** (new): manual client link/unlink UI is minimal
  (link-by-UUID, no search).
- **TD-005** (new): `client_facts` are derived from `memory.topics`
  (labels), not dedicated preference extraction.
- **TD-006** (new, highest priority): `Person.role` is never
  populated by extraction, so FD-003's automatic matching is
  currently inert against real data — see `Sprint3.md`.

## Next sprint

Sprint 5 should focus on production readiness: authentication and tenant
isolation, background processing with retries, queue pagination, and stronger
client identity resolution. Sprint 4's command center is complete and provides
the product surface those capabilities will support.
