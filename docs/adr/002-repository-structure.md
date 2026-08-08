# ADR-002: Repository Structure

## Status
Accepted — routing and domain-event placement superseded by ADR-004
(Sprint 1). Everything else in this ADR (domain package boundaries,
`repositories/`/`services/`/`orchestrator/` as shared base-class
packages) still holds.

**Sprint 2 amendment (approved, not a new ADR):** `app/orchestrator/`
now also holds concrete cross-slice orchestrators (starting with
`ConversationProcessingOrchestrator`), not only `BaseOrchestrator`.
This is the "workflow spans multiple domains" case this ADR already
described — Sprint 2 is simply the first sprint where that case
actually occurred. See the "Sprint 2: first concrete orchestrator"
section below for the reasoning.

## Context
ConversationOS will grow to cover multiple domains (conversations,
clients, memory, communication, tasks, organizations, integrations)
across multiple verticals. A flat or feature-less structure would
make it hard to keep business logic, data access, and API surface
cleanly separated as the codebase grows — and hard for future
engineers to find "where does X live" quickly. The structure also
needs to support workflows that span more than one domain (Sprint 1's
Conversation → Transcript → Knowledge → Actions → Timeline →
Communication pipeline is the first example), without forcing one
domain to reach directly into another's internals.

## Decision
Adopt a monorepo with a strict frontend/backend split at the top
level, and a domain-oriented package layout inside the backend:

```
conversation-os/
  backend/app/
    api/                     # composition root only as of ADR-004 — mounts each slice's router
    core/                    # config, logging, database
    shared/                  # domain-agnostic utilities, cross-domain
    repositories/            # BaseRepository (Rule 2)
    services/                # BaseService (Rule 3)
    orchestrator/            # BaseOrchestrator — coordinates multi-step,
                              #   multi-domain workflows
    providers/                # AIProvider abstraction (Rule 6)
    conversation/ client/ memory/ communication/
    tasks/ organization/ integrations/ events/  # domain packages
    models/ schemas/
  backend/tests/
  frontend/
  docs/{product,architecture,engineering,adr,api,deployment}
  docker/
  infrastructure/
  scripts/
  .github/
```

Two structural layers work together here:

- **Base-class packages** (`repositories/`, `services/`, `orchestrator/`)
  hold the abstract contracts every domain follows —
  `BaseRepository`, `BaseService`, `BaseOrchestrator`. They contain no
  business logic and no concrete domain code.
- **Domain packages** (`conversation/`, `client/`, etc.) hold each
  domain's *concrete* repositories, services, models, and schemas,
  subclassing the base classes above. Sprint 0 only creates the
  domain folders and `__init__.py` stubs, per the "no business
  features" constraint — the first concrete subclasses land in
  Sprint 1.

`app/core` holds cross-cutting concerns (config, logging, database)
that every domain depends on but that don't belong to any one domain.
`app/shared` is reserved for domain-agnostic utilities that don't fit
the repository/service/orchestrator shape (e.g. shared value objects,
formatting helpers) — nothing lives there yet in Sprint 0.

## Consequences
- New domains are added by creating a new top-level package under
  `app/`, not by nesting further inside an existing one — keeps
  domain boundaries flat and visible.
- A workflow that spans multiple domains gets a dedicated
  orchestrator subclass instead of one service quietly importing
  another domain's service — keeps cross-domain coordination
  explicit and easy to find.
- Docs are split by audience (`product/`, `architecture/`,
  `engineering/`, `api/`, `deployment/`) plus a dedicated `adr/`
  folder so architectural history doesn't get buried in narrative
  docs.
- This structure is heavier than a single-file "hello world" backend
  Sprint 0 would technically need — that overhead is intentional,
  since the point of Sprint 0 is to absorb structural cost before
  business logic exists, not after.

## Sprint 2: first concrete orchestrator (amendment)

Sprint 2 introduced `app/orchestrator/conversation_processing.py` —
`ConversationProcessingOrchestrator`, the first concrete
`BaseOrchestrator` subclass. It coordinates three slices
(`conversation`, `transcription`, `memory`) through one pipeline:
transcribe → extract → persist → update conversation status.

**Where it lives, and why that's not a new decision.** This ADR's
original "Consequences" section already named the case: *"a workflow
that spans multiple domains gets a dedicated orchestrator subclass."*
Sprint 0–1 never exercised that case because no workflow spanned two
slices yet. Sprint 2 is simply the first time it did. Putting the
concrete class in `app/orchestrator/` alongside `BaseOrchestrator`
(rather than inside `conversation/`, `transcription/`, or `memory/`)
follows from the same logic as `app/api/router.py` being a
composition root in its own file rather than living inside whichever
slice happens to be mounted first: a thing that inherently coordinates
multiple slices shouldn't appear to belong to just one of them.

**Construction is a plain function, not a FastAPI dependency.** The
orchestrator needs two provider factories
(`get_ai_provider`/`get_transcription_provider`) that raise a clear
error if their API keys aren't configured. If the orchestrator itself
were injected via `Depends(...)`, that error would surface during
FastAPI's dependency-resolution phase — before the route body runs —
which would make a missing API key block the *upload* itself, not
just downstream processing. `app/orchestrator/dependencies.py`
exposes a plain `build_conversation_processing_orchestrator(...)`
function instead, called manually inside `conversation/api.py`'s
upload handler, wrapped in its own `try/except` so upload success and
processing failure stay independent. This is a small, deliberate
deviation from "everything is a FastAPI dependency," scoped narrowly
to this one error-handling requirement — not a general pattern change.

**Synchronous execution (TD-003).** The orchestrator runs inside the
upload request rather than as a background task. See `Sprint2.md`'s
Technical Debt section for the tradeoff; it's tracked, not hidden.
