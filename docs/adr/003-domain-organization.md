# ADR-003: Domain Organization & Architectural Rules

## Status
Accepted

## Context
Without enforced boundaries, it's easy for a fast-moving team to let
business logic leak into API routes, or database queries leak into
services — both of which make the codebase brittle as more domains
(conversation, client, memory, communication, tasks, organization,
integrations) are added in future sprints. ConversationOS also
depends on multiple AI providers (OpenAI, Anthropic, Gemini), and
coupling business logic directly to any one vendor's SDK would make
provider changes expensive.

## Decision
Six architectural rules apply across the codebase, starting now:

1. **Business logic must never exist inside API routes.** Routes only
   parse input, call a service, and shape the response.
2. **Database access must occur through repositories.** Services never
   issue raw queries or touch the SQLAlchemy session directly. The
   shared contract lives in `app/repositories/base.py`; each domain
   subclasses it once it has real tables.
3. **Services contain business logic.** This is the only layer allowed
   to make domain decisions. The shared contract lives in
   `app/services/base.py`; each domain subclasses it once it has real
   behavior.
4. **Configuration must be centralized.** All environment-driven
   config lives in `app/core/config.py`; nothing else reads
   `os.environ` directly.
5. **Everything should be modular.** Domains (`conversation/`,
   `client/`, etc.) are self-contained packages; cross-domain
   dependencies should be explicit, not implicit via shared globals.
   Where a workflow genuinely spans multiple domains, it goes through
   an orchestrator (`app/orchestrator/base.py`) rather than one
   domain's service reaching directly into another's.
6. **AI must be abstracted.** Business logic depends on the
   `AIProvider` interface (`app/providers/ai_provider.py`), never on
   `openai` or `anthropic` SDKs directly. Concrete providers
   (`OpenAIProvider`, `ClaudeProvider`, `GeminiProvider`) plug into
   that interface in a future sprint.

None of `repositories/base.py`, `services/base.py`, or
`orchestrator/base.py` contain business logic or domain-specific code
as of Sprint 0 — they exist only so Sprint 1's first domain
implementation has a contract to subclass on day one, instead of
inventing one under deadline pressure.

## Consequences
- Adding a new AI vendor later means implementing one new
  `AIProvider` subclass — no changes to business logic.
- Swapping the ORM, or moving a domain to its own service later,
  is a repository-layer change, not a service-layer rewrite.
- A multi-domain workflow (Sprint 1's conversation-processing
  pipeline being the first) gets one orchestrator class to read,
  instead of tracing an implicit call chain across several services.
- This adds a layer of indirection (route → service → repository)
  that a throwaway prototype wouldn't need. That's an accepted
  tradeoff: ConversationOS is explicitly designed to outlive its
  first vertical (Realtors) and expand into others.
- Enforcement is currently manual (code review), not automated by a
  linter rule — a risk worth revisiting once the domain folders
  contain real code in Sprint 1.
