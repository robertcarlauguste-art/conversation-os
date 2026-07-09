# Sprint 0 — Engineering Foundation

**Status:** Complete. Ready for Architecture Review before Sprint 1 begins.

## 1. Repository Tree

```
conversation-os/
├── .env.example
├── .gitignore
├── README.md
├── docker-compose.yml
├── .github/workflows/
│   ├── backend-ci.yml       # ruff, black, mypy, pytest
│   └── frontend-ci.yml      # eslint, typecheck, build
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/0001_initial_baseline.py   # enables pgvector, no tables
│   ├── app/
│   │   ├── main.py                # FastAPI app assembly
│   │   ├── api/system.py          # GET /health, GET /version — only routes in scope
│   │   ├── core/                  # config.py, database.py, logging.py
│   │   ├── repositories/base.py   # BaseRepository (Rule 2)
│   │   ├── services/base.py       # BaseService (Rule 3)
│   │   ├── orchestrator/base.py   # BaseOrchestrator — multi-domain workflow coordination
│   │   ├── providers/ai_provider.py  # AIProvider interface (Rule 6)
│   │   └── conversation/ client/ memory/ communication/
│   │       tasks/ organization/ integrations/ events/
│   │       models/ schemas/       # empty domain packages, Sprint 1+
│   └── tests/test_system.py
├── frontend/                      # Next.js 15 + TS + Tailwind app router
│   ├── Dockerfile
│   ├── package.json
│   └── src/app/{layout.tsx,page.tsx,globals.css}
├── docs/
│   ├── product/README.md
│   ├── architecture/README.md
│   ├── engineering/README.md
│   ├── adr/{001-tech-stack.md, 002-repository-structure.md, 003-domain-organization.md}
│   ├── api/README.md
│   └── deployment/README.md
├── docker/README.md
├── infrastructure/README.md
└── scripts/README.md
```

## 2. Architecture Summary

The backend follows a route → service → repository layering
(services aren't implemented yet since there's no business logic in
Sprint 0, but the routes and repository base class are already
shaped to enforce it). `app/core` centralizes configuration, database
session management, and structured logging so no other module reads
environment variables or opens a DB connection directly. Each future
business domain (conversation, client, memory, communication, tasks,
organization, integrations, events) gets its own top-level package
under `app/`, currently empty stubs. AI access is abstracted behind
an `AIProvider` interface with zero vendor SDK usage yet — see
ADR-001 through ADR-003 for the full reasoning.

The frontend is a standard Next.js 15 App Router project with
TypeScript strict mode and TailwindCSS configured; no pages beyond a
placeholder home route exist yet, since UI work is out of scope.

## 3. Code Walkthrough

| File | Purpose |
|---|---|
| `backend/app/main.py` | Assembles the FastAPI app: middleware + router only, no logic. |
| `backend/app/api/system.py` | `/health` and `/version` — the only two endpoints in scope. |
| `backend/app/core/config.py` | Single source of truth for all env vars (Rule 4). |
| `backend/app/core/database.py` | Async SQLAlchemy engine/session factory. |
| `backend/app/core/logging.py` | Structured request logging (request id, timestamp, duration, status). |
| `backend/app/repositories/base.py` | Generic `BaseRepository` — domain repos will subclass this. |
| `backend/app/services/base.py` | Generic `BaseService` — domain services will subclass this. |
| `backend/app/orchestrator/base.py` | `BaseOrchestrator` — coordinates multi-domain workflows (e.g. Sprint 1's conversation pipeline). |
| `backend/app/providers/ai_provider.py` | `AIProvider` abstract interface; no concrete provider implemented. |
| `backend/alembic/versions/0001_initial_baseline.py` | Enables the `pgvector` Postgres extension; no app tables. |
| `frontend/src/app/*` | Minimal Next.js App Router scaffold with Tailwind wired in. |

## 4. Setup Instructions

See the root `README.md` — `docker compose up` launches frontend,
backend, Postgres, and Redis together; the README also covers running
each service locally without Docker.

## 5. ADR Summary

- **ADR-001 (Technology Stack):** Locks Next.js 15 / FastAPI / Postgres
  + pgvector / Redis, chosen for async-first I/O and built-in vector
  search support ahead of Sprint 1's memory features.
- **ADR-002 (Repository Structure):** Monorepo with a domain-oriented
  backend package layout so each business domain gets its own flat,
  visible package as the app grows.
- **ADR-003 (Domain Organization):** Codifies the six architectural
  rules (no logic in routes, DB access only via repositories, services
  own business logic, centralized config, modularity, AI abstraction).

## 6. Risks / Architectural Concerns Discovered

- **`target_metadata = None` in Alembic.** Until `app/models/base.py`
  defines a declarative base, `alembic revision --autogenerate` won't
  detect model changes automatically — fine for Sprint 0 (no tables),
  but worth flagging before Sprint 1's first real migration.
- **No rate limiting / API versioning scaffold.** Not required by
  Sprint 0's Definition of Done, but worth a decision before external
  integrations (Sprint 1+) start hitting the API.
- **Frontend has no API client wired to TanStack Query yet** — it's
  installed but unused, since there's no backend data to fetch. Sprint
  1 will need to decide on the fetch/query-key convention.
- **CI installs backend dev dependencies as a flat pip/uv list**
  rather than via `pyproject.toml`'s `[dependency-groups]`, because
  `uv pip install --group` syntax varies by uv version. Low risk, but
  worth revisiting once uv's dependency-group support stabilizes.

## 7. Recommendations for Sprint 1

1. Define `app/models/base.py` (SQLAlchemy declarative base) before
   the first real migration, so Alembic autogenerate works from the
   start.
2. Build the Conversation domain first (per the spec's Sprint 1
   preview: Conversation → Transcript → Knowledge → Actions →
   Timeline → Communication) — it's the core workflow everything else
   hangs off of.
3. Decide on the TanStack Query data-fetching convention (query key
   structure, error handling pattern) before the first real page is
   built, so it's consistent from page one rather than retrofitted.
4. Hold the planned Architecture Review before writing Sprint 1 code,
   per the working agreement — this is the right moment to catch
   structural issues while the codebase is still small.

## Sprint 0 Refinements (this pass)

- Added `app/repositories/`, `app/services/`, and `app/orchestrator/`
  as dedicated base-class packages (moved `BaseRepository` out of
  `app/shared/`, added `BaseService` and `BaseOrchestrator`). No
  business logic added — these are abstract contracts only, and no
  domain model changed.
- **Found and fixed a real bug** in `app/core/logging.py`: the
  request-logging middleware was reading a `request._status_code`
  attribute that was never set, so every request logged status `"-"`
  instead of the real response status. It now reads
  `response.status_code`, guards against the case where an exception
  occurs before a response exists, and is covered by a new test
  (`test_unknown_route_returns_404_with_request_id`) asserting a
  non-2xx response still gets logged and still returns the
  `X-Request-ID` header.
- Polished `README.md` (new Observability section, updated repo tree)
  and ADR-002 / ADR-003 to describe the new base-class layer and how
  domain packages will subclass it in Sprint 1.
- Re-ran the full verification suite after these changes: `pytest`
  (3/3 passing), `ruff check`, `black --check`, and `mypy` all clean.

## Verification performed this sprint (not just claimed)

- `pytest` — 3/3 tests pass (`/health`, `/version`, 404 + request-id).
- `ruff check`, `black --check`, `mypy` — all clean on the backend.
- `npm install && next build` — frontend compiles and produces a
  production build successfully.
- `docker-compose.yml` — parsed and validated as well-formed YAML
  with the four expected services (postgres, redis, backend, frontend).
  Full `docker compose up` was not run in this sandbox (no Docker
  daemon available here) — recommend a manual run before merging.
