# Architecture

System-level architecture, distinct from individual decisions (which
live in [`adr/`](../adr)).

## Current shape (as of Sprint 3)

ConversationOS follows a **hybrid layered / vertical-slice**
architecture (see [ADR-002](../adr/002-repository-structure.md),
[ADR-004](../adr/004-vertical-slice-architecture.md), and
[ADR-005](../adr/005-client-matching-strategy.md)):

- **Shared infrastructure** (`app/core`, `app/repositories`,
  `app/services`, `app/orchestrator`, `app/providers`, `app/models`,
  `app/schemas`) holds cross-cutting concerns and abstract base
  classes — plus concrete cross-slice orchestrators (ADR-002's Sprint
  2 amendment).
- **Vertical slices** (`app/conversation/`, `app/transcription/`,
  `app/memory/`, `app/client/`, and one per future business
  capability) own everything specific to that capability: routes,
  service, repository, models, schemas, and domain events.
- **`app/api/router.py`** is a composition root: it mounts every
  slice's router under the FastAPI app and contains no logic of its
  own.
- **`app/orchestrator/conversation_processing.py`** now coordinates
  four slices (`conversation`, `transcription`, `memory`, `client`)
  through one pipeline, with the client-reconciliation stage isolated
  in its own `try/except` so a matching failure doesn't erase an
  otherwise-successful transcription+extraction.

## The pipeline

Per the product owner's direction starting Sprint 1, every future
capability is a stage in one pipeline rather than an isolated feature:

```
Conversation → Intake → Transcription → Knowledge Extraction
→ Relationship Memory → Recommendations → Actions
```

Sprint 1 delivered **Intake**. Sprint 2 delivered **Transcription**
and **Knowledge Extraction** together. Sprint 3 delivers
**Relationship Memory** — with an important caveat: automatic
matching is implemented but currently inert against real data, since
Sprint 2's extraction doesn't yet capture a corroborating attribute
per person (see `Sprint3.md` and ADR-005). **Recommendations** and
**Actions** remain future work.

## Diagrams

None yet — the system is still small enough that the file tree and
the ADRs are the accurate source of truth. Worth adding a sequence
diagram for `ConversationProcessingOrchestrator.run()` now that it
coordinates four slices — this is the point where holding the
sequence in your head from the code alone starts to get harder.

