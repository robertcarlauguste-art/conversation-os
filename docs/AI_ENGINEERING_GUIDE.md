# AI Engineering Guide

**Status:** Living document. This is the process ConversationOS is
built by, not a one-time sprint deliverable — update it when the
process itself changes, not when a sprint ships.

This guide exists because ConversationOS is built across two AI
collaborators (a Solutions Architect/CTO and an Implementation
Engineer) plus a human Founder, none of whom share memory between
sessions by default. Everything here is written so that a new
session — human or AI — can pick up the project correctly without
re-deriving decisions that have already been made.

---

## 1. Project Vision

See [`docs/product/VISION.md`](./product/VISION.md) for the full
statement. Summary, for engineering purposes:

ConversationOS is **not a CRM**. It's an intelligent layer that sits
on top of existing CRMs and turns conversations into structured
business knowledge — transcripts, extracted facts, remembered
preferences, follow-up tasks, drafted communications — without
requiring manual data entry.

**MVP market:** residential real estate. **Long-term:** any
relationship-driven business (mortgage, insurance, financial
advising, legal, healthcare, recruiting, consulting).

**Why this matters for engineering decisions:** every domain
boundary, every abstraction (`StorageBackend`, `AIProvider`,
`TranscriptionProvider`), and the vertical-slice structure itself
exist because the product is expected to generalize past real estate.
When a design choice trades a little Sprint N complexity for not
having to redo work in Sprint N+8 for a new vertical, take the trade.
When it doesn't serve that goal, don't add it "just in case" —
YAGNI still applies; generalize toward the stated verticals, not
toward hypothetical ones.

The product pipeline every sprint is a stage of:

```
Conversation → Intake → Transcription → Knowledge Extraction
→ Relationship Memory → Recommendations → Actions
```

---

## 2. Repository Rules

- **Monorepo**, strict `frontend/` / `backend/` split at the top
  level.
- **Hybrid layered / vertical-slice architecture** (ADR-002, ADR-004).
  Shared, logic-free infrastructure lives in `backend/app/{core,
  repositories, services, orchestrator, providers, models, schemas}`.
  Each business capability gets its own vertical slice under
  `backend/app/<slice_name>/`, shaped like `conversation/`,
  `transcription/`, or `memory/`:
  ```
  <slice>/
    api.py          # thin routes, mounted by app/api/router.py
    service.py       # business logic, subclasses BaseService
    repository.py     # persistence, subclasses BaseRepository
    models.py           # ORM models
    schemas.py           # Pydantic request/response schemas
    validators.py         # business validation rules (if any)
    events.py               # domain events (if any)
    tests/                    # slice-owned test suite
  ```
- **No new top-level folders** under `backend/app/` without deciding
  whether it's shared infrastructure (base classes/utilities only,
  no business logic) or a vertical slice (owns its own domain). If
  you're unsure which, that uncertainty is itself a signal to write
  an ADR before creating the folder, not after.
- **Slice naming: singular, `snake_case`**, matching the entity or
  capability it owns — `conversation/`, `transcription/`, `memory/`,
  not `conversations/` or `TaskManagement/`. This isn't cosmetic:
  the Product Backlog already names future capabilities (Task
  Generation, Email Drafting, CRM Integration); when one becomes a
  sprint, its slice name should be decided once, consistently, from
  this rule — not re-litigated per sprint.
- **Cross-slice imports are a smell, not a ban.** One is tolerable
  and should be logged as tracked technical debt (see TD-001 in
  `Sprint2.md` for the precedent: `transcription/` importing
  `conversation/storage.py` directly). Two or more slices depending
  on the same cross-slice import is the trigger to promote that code
  to shared infrastructure — don't wait for a third.
- **Workflows spanning multiple slices go through an orchestrator**
  (`app/orchestrator/`), never through one slice's service calling
  another slice's service directly. Concrete orchestrators live in
  `app/orchestrator/` alongside `BaseOrchestrator` (ADR-002's Sprint 2
  amendment) — a thing that coordinates multiple slices shouldn't
  appear to belong to just one of them.
- **No hardcoded paths, secrets, or magic config values.** Everything
  environment-dependent goes through `app/core/config.py`
  (`Settings`), full stop.

---

## 3. Architecture Principles

These are the six rules from ADR-003, unchanged since Sprint 0 and
still the load-bearing constraints on every PR:

1. **Business logic never lives in API routes.** Routes parse input,
   call a service, shape the response. This includes the composition
   root (`app/api/router.py`) — it mounts routers, it doesn't contain
   any.
2. **Database access happens only through repositories.** Services
   never issue raw queries or touch the SQLAlchemy session directly.
3. **Services contain business logic.** The only layer allowed to
   make domain decisions.
4. **Configuration is centralized.** `app/core/config.py` is the only
   place that reads environment variables.
5. **Everything is modular.** One slice per business capability;
   cross-domain coordination goes through an orchestrator, not an
   implicit import chain.
6. **AI is abstracted.** Business logic depends on `AIProvider` /
   `TranscriptionProvider` (or the next abstraction a new AI capability
   needs), never on a vendor SDK directly. A new vendor is a new
   subclass, not a business-logic change.

**Two structural layers work together, and both matter:**

- **Base-class packages** (`repositories/`, `services/`,
  `orchestrator/`, `providers/`) hold abstract contracts and, as of
  Sprint 2, concrete cross-slice coordinators. No business logic, no
  concrete domain code that belongs to one slice.
- **Domain packages** (`conversation/`, `transcription/`, `memory/`,
  ...) hold each domain's concrete repositories, services, models,
  schemas — subclassing the base classes above.

When a new capability needs a new *kind* of abstraction (the way
Sprint 2 needed `TranscriptionProvider` alongside `AIProvider`), ask
whether it's a genuinely different shape of problem before reusing an
existing interface. Forcing two different capabilities into one
interface to avoid writing a second one is a false economy — it was
worth having two provider interfaces in Sprint 2 specifically because
audio-in/text-out and messages-in/text-out are different enough
shapes that one interface would have made both harder to use
correctly.

---

## 4. ADR Policy

- **One file per decision**, in `docs/adr/`, named
  `NNN-short-description.md`. Not a single running document.
- **ADRs are immutable once accepted.** A later decision that changes
  or narrows an earlier one gets a new ADR that supersedes it (in
  whole or in part) — or, for a small, clearly-scoped extension that
  doesn't contradict the original reasoning, an **amendment section**
  appended to the original ADR with its own heading (see ADR-002's
  "Sprint 2 amendment" for the pattern). Use judgment on which:
  - **New ADR** if the change reverses a prior decision, introduces a
    new category of tradeoff, or would confuse someone reading the
    original ADR without the update.
  - **Amendment to the existing ADR** if the change is the original
    ADR's own stated logic playing out for the first time (e.g.
    ADR-002 predicted "a workflow spanning multiple domains gets an
    orchestrator" — Sprint 2 doing exactly that is confirmation, not
    a reversal).
- **Template:** Status, Context, Decision, Consequences — add
  Alternatives Considered whenever more than one real option existed
  (see ADR-004 for the fullest example of this).
- **The `Status` line always says what's still true and what's been
  superseded/amended**, with a pointer to whichever ADR did it. Never
  leave a reader to guess whether an ADR is current.
- **`docs/founder/ENGINEERING_JOURNAL.md`** is a different, narrower
  tool: a running log of decisions/tradeoffs/lessons in chronological
  order, useful for "what happened and why, in order" narrative. It
  does not replace ADRs — an entry there pointing at an ADR is fine;
  an ADR's worth of reasoning living only in the journal is not.
- **Architectural conflicts get surfaced, not resolved silently.** If
  implementing a sprint spec would contradict an existing ADR, stop
  and explain the conflict with the available options before writing
  code — this has happened twice already (Sprint 1's Vertical Slice
  vs. Sprint 0's layered routing; Sprint 2's missing transcription
  step) and both times surfacing it first, rather than picking an
  interpretation silently, was the right call.

---

## 5. Git Workflow

- **Feature branches**, named `feature/<short-description>` (or
  `feature/COS-NNN-<short-description>` if/when ticket numbers exist).
  No direct commits to `main`.
- **`main` is always deployable.** A feature branch merges to `main`
  only after: the Founder has reviewed the diff (the review-before-
  commit step above only covers getting a change *onto* the branch;
  this is the separate, later approval to bring it into `main`), CI
  is green on the branch, and the sprint's Definition of Done
  (Section 10) is satisfied. Committing to a feature branch is not
  the same approval as merging it — treat them as two distinct
  sign-offs even when they happen in the same conversation.
- **The local repository at `C:\Users\Robert\Projects\conversation-os`
  is always the authoritative codebase.** An AI implementation
  session's sandbox is a workspace, not a source of truth — nothing
  is "done" until it exists in the real repository. If a sandbox
  session's work only exists as sandbox state (not committed, not
  bundled, not delivered), it should be treated as **not done**,
  regardless of how complete it looked in that session.
- **Syncing sandbox work into the real repo happens via `git bundle`,
  not ZIP files or manual file copying**, once a repository already
  exists with real history:
  1. Founder runs `git bundle create <name>.bundle --all` in the real
     repo and shares the bundle.
  2. The AI session clones the bundle (`git clone <name>.bundle`),
     confirms real history is present (`git log --oneline --all`)
     before touching anything, and works on a feature branch.
  3. Every file the session intends to modify gets read from the
     actual clone first — never assumed from a prior session's
     memory of what the file "should" contain. (This guide's own
     Sprint 2 was written this way after a mismatch surfaced between
     sandbox-assumed and actual repository content.)
  4. When implementation is complete and verified, the session stops
     **before committing** and presents `git status`, `git diff
     --stat`, new/modified file lists, test results, and a suggested
     commit message for review.
  5. Only after explicit approval does the session commit — and even
     then, only produces an updated bundle / pushes if explicitly
     asked to. Commit ≠ push ≠ merge to main; each is a separate,
     explicit approval.
- **Never rewrite history** (no force-push, no rebase of shared
  branches, no amending commits that have already been shared back)
  unless explicitly instructed.
- **Commit messages**: a `type: summary` first line (`feat:`, `fix:`,
  `docs:`, `refactor:`, `chore:`), followed by a body that explains
  *why*, notably including any tracked technical debt introduced and
  any tradeoffs made. See `Sprint2.md`'s suggested commit message for
  the expected level of detail — a reviewer should be able to
  understand the change's shape and its known gaps from the commit
  message alone, without re-reading the diff.

---

## 6. Sprint Workflow

ConversationOS is built through a three-role pipeline (see Section 11
for the roles). Per sprint:

1. **Founder sets the sprint theme and priority** (product direction,
   what problem this sprint solves for the end user).
2. **CTO/Solutions Architect produces a sprint specification**:
   user stories, technical requirements, explicit scope and
   out-of-scope lists, and a Definition of Done. Nothing skips this —
   implementation does not begin from a Founder request alone without
   a specification the Implementation Engineer can execute against.
3. **Implementation Engineer confirms repository connectivity
   (Section 12's first checklist item), then reviews the spec against
   the existing codebase before writing code**: identifies
   architectural consistency or conflicts, produces a short
   implementation plan, and — critically — **stops and asks before
   resolving any conflict or scope gap**, rather than silently
   picking an interpretation. Two real examples from this project:
   Sprint 1's spec asked for Vertical Slice Architecture in a way that
   contradicted Sprint 0's ADR-002, and that was raised and resolved
   as a hybrid before any code was written; Sprint 2's spec had no
   transcription step even though its pipeline needed transcribed
   text, and that scope gap was raised and the Founder chose to
   expand scope rather than stub it.
4. **Implementation proceeds only within approved scope.** An
   "explicitly out of scope" list in a sprint spec is binding — don't
   build ahead of a planned sprint even if it looks convenient to do
   opportunistically.
5. **Verification happens against real infrastructure**, not just
   claimed (see Section 12).
6. **A sprint deliverable document** (`SprintN.md`) is produced —
   see Section 9 for required contents.
7. **A formal Architecture Review happens between sprints**, before
   the next sprint's implementation begins — this is a deliberate
   pause, not a formality to skip. It's the point to catch structural
   issues while the codebase is still small enough that fixing them
   is cheap.
8. **Nothing is committed without explicit review and approval** of
   the diff, file list, and test results first (see Section 5).

---

## 7. Testing Requirements

- **Real infrastructure over mocks, wherever practical.** Tests run
  against a real Postgres instance (with pgvector), not SQLite or an
  in-memory substitute — several of this project's ORM column types
  (Postgres `ARRAY`, `ENUM`, `UUID`) aren't portable to SQLite, and a
  passing SQLite test suite would not actually prove the migrations
  or queries work.
- **External network calls (AI vendors) are faked, not skipped.**
  Fakes implement the real abstraction (`AIProvider`,
  `TranscriptionProvider`) so the real orchestrator/services/database
  all execute for real — only the outbound HTTP call to
  `api.anthropic.com` / `api.openai.com` is replaced. See
  `backend/tests/fakes.py`. This keeps tests fast, free, and
  deterministic while still exercising real code paths, not test
  doubles standing in for entire slices.
- **Required test types per slice**, mirroring `conversation/`,
  `transcription/`, and `memory/`:
  - **Validator tests** — business rules in isolation, no DB/network.
  - **Repository tests** — against real Postgres: add/get, sort
    order, missing-record lookups, deletes, cascades.
  - **Service tests** — integration-level, real DB + fake external
    providers where relevant: the success path and at least one
    realistic failure path (bad input, provider error).
  - **API tests** — through the real FastAPI app (`ASGITransport`),
    covering success, validation failure (4xx), and not-found (404)
    at minimum.
  - **Integration tests** for anything that spans multiple slices —
    e.g. `conversation/tests/test_api.py`'s pipeline test, which
    patches only the two external provider factories and lets the
    real orchestrator run end to end.
- **Both the "it works" and "it fails gracefully" paths need a
  test.** A missing API key, a malformed LLM response, or a missing
  file should never crash a request with a 500 if there's a
  documented graceful-degradation behavior — write the test that
  proves the degradation, not just the happy path.
- **All tests must pass before a sprint is considered complete.** No
  merging or delivering with known-failing tests, even temporarily.
- **CI mirrors local verification exactly.** If a dependency list,
  migration step, or environment variable is needed for tests to
  pass locally, `.github/workflows/backend-ci.yml` needs the same —
  verify this by actually simulating CI's exact install/test sequence
  locally before trusting the workflow file, not by assuming it
  matches.

---

## 8. Code Quality Standards

- **Backend:** `ruff check`, `black --check`, and `mypy` must all be
  clean. Type hints required throughout — no untyped public
  functions. No wildcard imports.
- **Frontend:** `eslint` and `tsc --noEmit` must both be clean; a
  production `next build` must succeed (not just `next dev` working).
- **Docstrings explain *why*, not just *what*.** A docstring that
  restates the function signature in prose is not useful; one that
  explains the design tradeoff, the historical reason a pattern
  exists, or what would break if this were done differently, is. See
  `app/conversation/storage.py` or `app/orchestrator/dependencies.py`
  for the expected density of "why" in a docstring.
- **Prefer clarity over cleverness.** Simplicity is a stated
  engineering value for this project (carried from the Sprint 1 CTO
  note: "favor simplicity over cleverness") — don't introduce a
  message broker, background worker, or new abstraction layer until
  a concrete, current need justifies it. Track the deferred need as
  technical debt (Section 9) instead of building it speculatively.
- **No dead placeholders left unexplained.** If a field, column, or
  code path exists but isn't populated/used yet (e.g.
  `duration_seconds`, `action_items.owner`), say so explicitly in a
  comment or the sprint doc — don't leave a future reader to wonder
  whether it's a bug.

---

## 9. Documentation Requirements

Every sprint updates, as applicable:

- **`SprintN.md`** (repo root) — required contents:
  - Scope, including any Founder-approved mid-sprint expansion or
    reduction (state it explicitly — don't let scope drift show up
    only in the diff).
  - Architecture summary and data model changes.
  - API surface changes and frontend changes.
  - Test summary (what was run, pass/fail counts).
  - **What was verified live vs. not** — any external dependency
    (vendor API, real device, etc.) not actually exercised gets
    named explicitly here, not just implied by its absence.
  - **Technical debt**, new and carried-forward, using sequential
    `TD-NNN` numbers that persist across sprints (Sprint 2 introduced
    TD-001–TD-003; Sprint 3's new debt starts at TD-004, and Sprint
    2's still-open items get re-listed with their status, not
    dropped). If this list outgrows a per-sprint doc, promote it to a
    standalone `TECH_DEBT.md` — but don't create that file
    speculatively before the list actually needs it.
  - Assumptions made (see below).
  - Recommendations for the next sprint.
- **`README.md`** — setup instructions, API endpoint table, database
  schema, repository structure diagram, and the "next sprint" pointer
  must reflect current reality, not the sprint they were last edited
  in.
- **ADRs** (`docs/adr/`) — for any new or amended architectural
  decision (Section 4).
- **`docs/api/README.md`** — endpoint table, kept in sync with actual
  routes (the live `/docs` Swagger UI is the source of truth for
  request/response shapes; this file is for the workflow-level
  summary and status-code conventions).
- **`docs/architecture/README.md`** — current-shape summary and the
  pipeline-stage mapping (which sprint delivered which stage).
- **`docs/features/<feature-name>.md`** — one per major user-facing
  workflow (e.g. `conversation-intake.md`, `memory-intelligence.md`),
  written for someone who needs to understand *how the feature works
  end to end*, not just its API surface.
- **`.env.example`** — every new environment variable, with a comment
  explaining what it's for and whether it's required or has a safe
  default/degradation path.
- **Assumptions get written down, not just made.** If a sprint spec
  is ambiguous and a reasonable default was chosen rather than asked
  about, it goes in `SprintN.md`'s Assumptions section — the Founder
  should never have to reverse-engineer an unstated assumption from
  the diff.

---

## 10. Definition of Done

A sprint (or a discrete unit of work within one) is done only when
**all** of the following are true — not claimed true, verified true:

- [ ] The feature works end to end, demonstrated against real
      infrastructure (real Postgres, real HTTP requests through the
      actual app) — not just unit tests in isolation.
- [ ] All automated tests pass (Section 7).
- [ ] `ruff`, `black --check`, and `mypy` are clean on the backend;
      `eslint`, `tsc --noEmit`, and a production build are clean on
      the frontend.
- [ ] Database migrations run cleanly against a real Postgres
      instance, both `upgrade` and (for anything non-trivial)
      `downgrade`.
- [ ] Any new external dependency (vendor API, package) that
      couldn't be exercised live in the build environment is
      explicitly flagged, with what still needs a real smoke test
      before production use — never silently assumed to work.
- [ ] Documentation is updated per Section 9.
- [ ] Any architectural conflict discovered during implementation was
      surfaced and resolved with the Founder before proceeding, not
      worked around silently.
- [ ] Technical debt introduced is logged in `SprintN.md`'s
      Technical Debt section using the next sequential `TD-NNN`
      number (Section 9) — not left implicit in the diff.
- [ ] `SprintN.md` is written (Section 9).
- [ ] Nothing has been committed without an explicit review step
      (`git status` / `git diff --stat` / file lists / test results)
      presented first, per Section 5.

---

## 11. AI Collaboration Workflow (Founder, CTO, Implementation Engineer)

ConversationOS is built through three distinct roles. Keeping them
distinct — even though two of them are AI — is what keeps decisions
traceable and prevents any one session from quietly accumulating
authority it wasn't given.

### Founder (Robert)
- Owns product direction, priority, and **all approvals**: scope
  changes, architectural amendments, vendor choices, and every
  commit/push/merge action.
- Is the only party who can authorize skipping or altering this
  process for a specific case.
- Reviews sprint deliverables and diffs before they're committed.

### CTO / Solutions Architect (upstream planning AI)
- Produces sprint specifications: user stories, technical
  requirements, data model, explicit scope and out-of-scope lists,
  Definition of Done.
- Owns architecture-level product decisions (e.g. "commit to a
  pipeline architecture" — the Sprint 1 CTO note establishing the
  Conversation → Intake → ... pipeline as the organizing structure).
- Does not write implementation code.

### Implementation Engineer (Claude, this role)
- Implements against the CTO's specification, inside the existing
  architecture, exactly as Section 6 describes.
- **Never resolves an architectural conflict or scope gap
  silently.** Surfaces it, proposes options with tradeoffs, and
  waits for a Founder decision before proceeding — this is not
  optional politeness, it's the mechanism that keeps the Founder in
  control of a codebase two different AI sessions are touching.
- **Never assumes sandbox state is repository state.** Verifies
  against the actual repository (via the git bundle workflow, Section
  5) before claiming anything is implemented, and is explicit about
  the difference between "written in my sandbox" and "in your
  repository" until a sync has actually happened.
- **Never claims verification that didn't happen.** If a real
  external API call, a specific environment, or a piece of
  infrastructure wasn't actually exercised, says so plainly rather
  than implying it was tested by proximity to things that were.
- **Stops before committing**, every time, regardless of how
  confident the implementation is, and waits for explicit sign-off.
- Tracks technical debt it introduces or discovers rather than either
  silently fixing out-of-scope problems or silently ignoring them.

### Why this matters in practice
Two failures this project has already hit and corrected for: (1) a
sandbox session's completed work was assumed to be "in the
repository" when it only existed in an isolated workspace — fixed by
adopting the git bundle workflow and treating "not yet in the real
repo" as "not done"; (2) sprint specifications have twice contained
gaps or conflicts with existing architecture that would have produced
silently-wrong software if implemented as literally written — fixed
by the Implementation Engineer stopping to ask both times. This
section exists so both fixes are process, not luck.

---

## 12. Repository Verification Checklist

**Run the first item below at the start of a session**, before any
implementation work — this is the specific check that would have
caught the Sprint 2 failure (a full sprint's worth of implementation
was completed in an isolated sandbox with no connection to the real
repository, and treated as progress rather than as a workspace
draft). **Run the rest before claiming any implementation is
complete** — sprint work, a bug fix, or a process change:

- [ ] **Is this session actually working from a clone of the
      Founder's real repository** (via the `git bundle` workflow,
      Section 5), or is it an unconnected sandbox/workspace? If the
      latter — state that plainly, to the Founder, before doing
      substantial work, not after. "I've implemented this" and "I've
      implemented this in your repository" are different claims;
      never let the first stand in for the second.
- [ ] Have I read the actual current content of every file I'm about
      to modify, in this session, rather than relying on memory of
      what a prior session wrote?
- [ ] Do real migrations run cleanly against a real Postgres instance
      (not assumed from a prior successful run in a different
      session/sandbox)?
- [ ] Does the real test suite pass, run in this session, against
      this code?
- [ ] Are `ruff` / `black` / `mypy` (backend) and `eslint` /
      `tsc --noEmit` / production build (frontend) all clean, run in
      this session?
- [ ] For any new external dependency (vendor API): is it clearly
      stated whether it was exercised live, or only implemented and
      reviewed? If only the latter, is that limitation written down
      somewhere the Founder will actually see it (not buried in a
      docstring alone)?
- [ ] Does `git status` / `git diff --stat`, run against the actual
      repository (bundle-cloned or otherwise confirmed authoritative),
      match what I'm about to describe as "changed"?
- [ ] Have I re-verified after any post-implementation edit (e.g. a
      reformat, a docs update)? A clean test run before a later edit
      does not certify the code after that edit.

---

## 13. Sprint Completion Checklist

- [ ] Sprint spec's Definition of Done fully satisfied (Section 10).
- [ ] `SprintN.md` written, per Section 9's required contents.
- [ ] Any ADR additions/amendments written (Section 4).
- [ ] `README.md`, `docs/api/README.md`, `docs/architecture/README.md`,
      relevant `docs/features/*.md`, and `.env.example` updated.
- [ ] Repository Verification Checklist (Section 12) fully passed.
- [ ] `git status`, `git diff --stat`, new-file list, modified-file
      list, test results, and a suggested commit message presented to
      the Founder — and nothing committed until approved.
- [ ] Formal Architecture Review scheduled/held before the next
      sprint's implementation begins.

---

*Last established: after Sprint 2 (Memory & Intelligence), before
Sprint 3 planning. Update the "Last established" line whenever this
guide's process — not just the product — changes.*