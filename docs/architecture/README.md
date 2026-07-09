# Architecture

System-level architecture, distinct from individual decisions (which
live in [`adr/`](../adr)).

## Current shape (as of Sprint 1)

ConversationOS follows a **hybrid layered / vertical-slice**
architecture (see [ADR-002](../adr/002-repository-structure.md) and
[ADR-004](../adr/004-vertical-slice-architecture.md)):

- **Shared infrastructure** (`app/core`, `app/repositories`,
  `app/services`, `app/orchestrator`, `app/providers`, `app/models`,
  `app/schemas`) holds cross-cutting concerns and abstract base
  classes. No business logic lives here.
- **Vertical slices** (`app/conversation/`, and one per future
  business capability) own everything specific to that capability:
  routes, service, repository, models, schemas, and domain events.
- **`app/api/router.py`** is a composition root: it mounts every
  slice's router under the FastAPI app and contains no logic of its
  own.

## The pipeline

Per the product owner's direction starting Sprint 1, every future
capability is a stage in one pipeline rather than an isolated feature:

```
Conversation → Intake → Transcription → Knowledge Extraction
→ Relationship Memory → Recommendations → Actions
```

Sprint 1 delivers **Intake** (the `conversation/` slice). The
`ConversationUploaded` domain event exists so **Transcription**
(Sprint 2) can subscribe to it without changing Sprint 1's code.

## Diagrams

None yet — the system is still small enough that the file tree and
the ADRs are the accurate source of truth. Worth adding sequence/
component diagrams here once a second slice exists and cross-slice
interaction (likely via `app/orchestrator/`) becomes real rather than
hypothetical.
