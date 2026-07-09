# ADR-004: Vertical Slice Architecture (Hybrid)

## Status
Accepted — supersedes the routing/events portion of ADR-002.

## Context
Sprint 1's spec called for Vertical Slice Architecture: each business
capability (starting with `conversation/`) owns its own `api.py`,
`service.py`, `repository.py`, `models.py`, `schemas.py`, `storage.py`,
`validators.py`, and `events.py`.

This created a direct conflict with ADR-002 (Sprint 0), which put all
routes in a global `app/api/` package (Rule 1) and treated `events/`
as its own top-level domain package rather than something each slice
defines locally. The spec itself instructed: *"If you discover
architectural conflicts, stop and explain them rather than working
around them silently."* That conflict was raised and resolved with
the product owner before any Sprint 1 code was written — see
"Alternatives" below for the options that were on the table.

Two things were **not** actually in conflict, despite first
appearances: `repository.py` and `service.py` inside a slice is
exactly what ADR-002 already planned (domain packages subclassing
`app/repositories/base.py` and `app/services/base.py`). The real
friction was narrower — routes and domain events.

## Decision
Adopt a **hybrid**: slices are genuinely vertical for everything
specific to that domain, while a thin composition root keeps FastAPI
wiring centralized.

- Each slice (e.g. `app/conversation/`) owns `api.py`, `service.py`,
  `repository.py`, `models.py`, `schemas.py`, `storage.py`,
  `validators.py`, `events.py`, and `tests/`.
- `app/api/router.py` is a **composition root only**: it imports each
  slice's router and mounts it (`api_router.include_router(...)`). It
  contains zero routes and zero logic of its own — Rule 1 still holds,
  because this file isn't a route, it's the thing that assembles them.
- `app/repositories/base.py`, `app/services/base.py`,
  `app/orchestrator/base.py` (added last refinement pass) remain
  shared, abstract infrastructure that every slice's concrete classes
  subclass — unchanged from ADR-002.
- `app/events/` (a Sprint 0 domain-package stub) is retired in favor
  of per-slice `events.py`. If a second slice needs to publish or
  subscribe to another slice's events, that mechanism becomes a
  shared event bus — likely living in `app/orchestrator/` — rather
  than slices importing each other's `events.py` directly. Not needed
  yet: Sprint 1's `ConversationUploaded` event has no consumers.

## Alternatives Considered
1. **Full Vertical Slice** — deprecate `app/api/`, `app/repositories/`,
   `app/services/` as separate layers entirely, let each slice be
   fully self-contained including its own base classes. Rejected:
   would duplicate the repository/service contract in every slice and
   lose the one-file-to-read guarantee ADR-002 was built around.
2. **Reject Vertical Slice** — keep all routes in global `app/api/`,
   let `conversation/` hold only `repository.py` + `service.py` +
   `models.py`. Rejected: this is what the spec explicitly asked to
   move away from, and it means route ownership crosses a package
   boundary from the domain that defines the request/response shape.
3. **Hybrid (chosen)** — described above.

## Consequences
- Adding a new slice means one new `include_router` call in
  `app/api/router.py`, plus the slice's own folder. No change to
  shared infrastructure required.
- A slice's routes, validation, storage, and events all live in one
  place — easier to review a single PR that changes one business
  capability, which was the original motivation for vertical slices.
- The shared base-class packages (`repositories/`, `services/`,
  `orchestrator/`) mean two slices can't silently diverge on how a
  repository or service is shaped — a real risk in a pure vertical
  slice setup with no shared contracts.
- `app/events/` sits empty as of this ADR (superseded by per-slice
  `events.py`) — worth deleting or repurposing rather than leaving it
  as a stale stub, flagged as a Known Issue in `Sprint1.md`.
- `storage.py` currently lives inside `conversation/` even though
  storage is a generic concern. It should move to shared
  infrastructure the moment a second slice needs file storage, rather
  than being duplicated — noted here so that moment isn't missed.
