# Sprint 3 — Relationship Memory

**Status:** Complete. Full pipeline verified end-to-end against real Postgres,
through the real HTTP API, with fake external providers standing in for the
two paid third-party AI calls (same pattern as Sprint 2). Implemented on top
of the still-uncommitted Sprint 2 work in this repository, per your
instruction not to commit.

## Founder Decisions applied

- **FD-003**: deterministic matching only. `ClientService.find_or_create`
  requires exact name match AND exact role match — role missing on either
  side means no automatic match is even attempted, and a new `Client` is
  created rather than guessed at. Never merges on name alone.
- **FD-004**: `backend/app/events/` — grepped for references first (zero
  found, confirmed before touching anything), deleted, then the complete
  test suite was re-run afterward (59/59 passed) before treating the
  deletion as final. Both conditions satisfied.
- **FD-005**: every `ClientFact` row carries `source_conversation_id`,
  `source_memory_id`, and `created_at` (the extraction timestamp) as
  required (non-nullable) columns — provenance isn't optional at the schema
  level, not just by convention.

## The most important finding this sprint

**FD-003's matching logic is correctly implemented but is currently inert
against real data.** Sprint 2's extraction (`ExtractionResult.people`) only
ever produces a list of names — `Person.role` is never populated anywhere in
the pipeline. Since automatic matching requires a role to even attempt a
match, **every real reconciliation this sprint creates a new `Client`
rather than ever matching an existing one.** Confirmed live: uploading a
conversation with two people (both `role=None`, since that's what real
extraction produces) created two brand-new clients, not zero.

This is the *safe, correct* consequence of FD-003 as written — the
alternative would be silently weakening "never merge on name alone" to
satisfy a feature demo — but it means Relationship Memory's headline
capability (US-101: recognizing returning clients automatically) doesn't
actually happen automatically yet. Fixing it means extending Sprint 2's
extraction prompt/schema to capture `role` (or, better, email/phone) per
person, which is out of this sprint's approved scope. Flagged here
explicitly rather than quietly patched around, and recommended as the
first item for Sprint 4.

## Architecture Summary

New `client/` vertical slice, exactly matching the established shape
(`api.py`, `service.py`, `repository.py`, `models.py`, `schemas.py`,
`validators.py`, `events.py`, `tests/`). `app/orchestrator/
conversation_processing.py` gained a fourth pipeline stage — reconciliation
— with its own `try/except` isolation, so a matching failure doesn't erase
an otherwise-successful transcription+extraction (conversation still
completes; only client-linking is skipped and logged).

**Primary-client heuristic** (needed since a conversation can mention
several people — buyer, seller, agent): the first extracted person whose
role isn't `"agent"` is treated as the conversation's primary client
(`conversations.client_id`); falls back to the first person if no
non-agent role is present. Documented as a simplification, not a claim of
certainty — this is the kind of judgment call that benefits from real
usage data before being treated as settled.

**No new provider abstraction** — deterministic matching (FD-003) needed
none; no `EmbeddingProvider` was introduced this sprint.

## Two implementation bugs found and fixed by actually running tests

1. **`MissingGreenlet` on `client.facts` access.** `BaseRepository.get()`
   uses `session.get()`, which shortcuts to the identity map for an object
   already loaded earlier in the same session (e.g. right after
   `find_or_create`), skipping the `facts` relationship's `selectin`
   eager-load. Fixed with `ClientRepository.get_with_facts()` — an explicit
   `select()` with `populate_existing=True`, which always re-applies eager
   loading regardless of identity-map state.
2. **Cross-test data pollution.** `ClientService` calls `commit()`
   internally (matching every other service in the codebase), so data
   written mid-test isn't undone by the test session's `rollback()` at
   teardown — `commit()` already finalized it. "Jane Smith"/"buyer" created
   in one test collided with the next test's assumption of a clean slate.
   Fixed with an autouse fixture in `client/tests/conftest.py` that
   truncates `client_facts`/`clients` before each test.

Neither of these would have been caught by writing tests without running
them — both surfaced only when the suite was actually executed.

## Database Changes

**`clients`**: `id`, `full_name`, `email` (nullable), `phone` (nullable),
`role` (nullable — last-reconciled role, used by the matcher; see
`models.py`'s docstring for why this isn't a live cross-slice query against
`people`), `created_at`, `updated_at`.

**`client_facts`**: `id`, `client_id` (FK, cascade delete), `fact_text`,
`source_conversation_id` (FK, cascade delete, **not nullable** — FD-005),
`source_memory_id` (FK, cascade delete, **not nullable** — FD-005),
`confidence` (nullable), `created_at` (the extraction timestamp).

**`conversations`**: `+ client_id` (nullable FK, `ON DELETE SET NULL`).
**`people`**: `+ client_id` (nullable FK, `ON DELETE SET NULL`).

Migration `0004` — **both `upgrade` and `downgrade` verified**, twice
(initial pass, and again after all fixes were applied) — the first time
this project has actually confirmed a downgrade path works, versus every
prior migration where only `upgrade` had been exercised.

**Design note on fact source**: rather than adding a new LLM-extracted
"client facts" field (would touch Sprint 2's tested extraction prompt,
out of scope), `client_facts` rows are derived from `memory.topics` —
data Sprint 2 already extracts. This is a real, deliberate scope-discipline
tradeoff: facts are currently topic labels ("financing", "timeline"), not
the richer preference statements ("prefers 3-bedroom homes") the product
vision describes. Documented as an assumption, not hidden.

## API Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/clients` | List clients, most recently updated first |
| `GET` | `/api/v1/clients/{id}` | Client profile with facts |
| `GET` | `/api/v1/clients/{id}/conversations` | Conversations linked to a client (US-104) |
| `POST` | `/api/v1/clients/{client_id}/conversations/{conversation_id}` | Manually link (US-105) |
| `DELETE` | `/api/v1/clients/{client_id}/conversations/{conversation_id}` | Manually unlink (US-105) |

Link/unlink construct `ConversationRepository` directly inside
`client/api.py` rather than going through the orchestrator — documented in
the route's own docstring as a deliberate proportionality choice (a
single-step, human-initiated action doesn't need multi-stage-workflow
machinery), following the same pattern `conversation/api.py` already used
for its own cross-slice wiring.

## UI Changes

- **`/clients`**: table (Name, Email, Phone, Added).
- **`/clients/[id]`**: remembered facts (with recorded-date + confidence)
  and linked conversations.
- **Conversation Detail**: new "Client" field — linked client name (link to
  their profile) with an Unlink action, or "Unmatched" with a minimal
  link-by-ID input. This is intentionally minimal (no search/autocomplete)
  — flagged as expected technical debt below, not silently shipped as if
  it were the intended final UX.
- Nav gained a "Clients" link. No new design tokens.

## Testing

**59/59 tests pass** (40 carried over from Sprint 1/2, unchanged and still
green — zero regressions — plus 19 new). New coverage:

- **Validators**: blank/oversized fact text.
- **Repository**: add/get, the FD-003 corroboration query directly
  (same name+role matches; same name+different role doesn't; different
  name doesn't), sorted listing, facts-with-provenance persistence.
- **Service** (the most important ground): `find_or_create`'s four cases —
  new client created, same name+role matches, same name+different role
  does NOT match, no role means NO automatic match attempted. Plus
  `record_facts`' provenance and validation.
- **API**: list, get, 404, link/unlink round-trip, unlinking against the
  wrong client correctly 404s.
- **Regression**: the existing Sprint 2 pipeline integration test
  (`conversation/tests/test_api.py`) still passes unmodified, now
  implicitly exercising the reconciliation stage too (since it runs
  through the real orchestrator).

`ruff`, `black --check`, `mypy` all clean. Frontend `eslint`,
`tsc --noEmit`, and a real production `next build` all pass (6/6 routes
compiled, including both new `/clients` routes).

**Live end-to-end smoke test** (not just automated tests): ran the actual
upload → transcribe → extract → reconcile pipeline through the real HTTP
API with fake external providers. Confirmed: two people with `role=None`
each created a new client (not a false match); facts were recorded with
correct provenance; a primary client was linked to the conversation;
manual unlink worked and correctly cleared `client_id`.

## Explicitly Out of Scope (honored)

Task Generation, Email Drafting, CRM/Calendar/SMS integration, mobile app,
analytics, team collaboration, AI meeting assistant, global cross-client
search, automatic duplicate-client merging, real-vendor smoke-testing of
`ClaudeProvider`/`OpenAIWhisperProvider`, and background job
infrastructure — none of these were touched.

## Technical Risks (as anticipated in the spec, now confirmed)

1. **Matching false positives/negatives** — mitigated by FD-003's
   conservative design, but the *practical* risk right now is the opposite
   problem: near-total false negatives (nothing auto-matches), documented
   above.
2. **Schema evolution regression risk** — mitigated: all 40 Sprint 1/2
   tests still pass unmodified.
3. **Inherited unverified risk from Sprint 2** — unchanged from Sprint 2's
   own disclosure; still applies.

## Technical Debt

- **TD-004 (new)**: manual-match UI ships minimal — link-by-pasting-a-UUID,
  no search/autocomplete, no "suggested matches" surfaced. Functional, not
  polished.
- **TD-005 (new)**: `client_facts` are derived from `memory.topics` (labels)
  rather than dedicated LLM-extracted preference statements. Upgrading this
  means touching Sprint 2's extraction prompt — a future sprint's decision,
  not made silently here.
- **TD-006 (new, the most important)**: `Person.role` is never populated by
  extraction, making FD-003's automatic matching currently inert against
  real data. See "The most important finding" above.
- **TD-001** (Sprint 2, re-evaluated): per the Engineering Guide's own
  threshold ("two or more slices trigger promotion to shared
  infrastructure"), still only one slice (`transcription/`) imports
  `conversation/storage.py` — `client/` didn't need storage. Left as-is,
  consistent with the Guide's rule, not Sprint2.md's looser recommendation
  to move it "in Sprint 3" — this was flagged as an open tension before
  implementation began, and resolved in the Guide's favor since it's the
  more precisely specified rule.
- **TD-002**: resolved this sprint (FD-004).
- **TD-003**: unchanged — still synchronous. Not addressed, since
  deterministic matching (the chosen approach) is cheap and doesn't create
  new latency pressure the way semantic/embedding matching would have.

## Assumptions Made This Sprint

1. `client_facts` sourced from `memory.topics`, not a new extraction field
   (see Database Changes).
2. Primary-client heuristic (first non-agent role wins) is a simplification
   pending real usage data.
3. Manual link/unlink UI is minimal by design this sprint (TD-004).
4. A reconciliation failure doesn't fail the whole conversation (mirrors
   Sprint 2's philosophy that a partial success is better than discarding
   real transcription/extraction work over a downstream hiccup).

## Recommendations for Sprint 4

1. **Highest priority**: decide whether to extend Sprint 2's extraction to
   capture `role` (cheap) or email/phone (better signal, more work) per
   person — without this, Relationship Memory's automatic matching stays
   inert against real conversations.
2. Revisit `client_facts` sourcing — dedicated preference extraction vs.
   continuing to reuse `topics`.
3. If usage reveals the primary-client heuristic picks wrong often, make
   it explicit/correctable at upload time rather than only after the fact.
4. TD-001 still open — reconsider once a third slice plausibly needs
   storage.
5. TD-003 still open — reconsider if/when matching logic gets more
   expensive (e.g. if semantic matching is adopted later).
