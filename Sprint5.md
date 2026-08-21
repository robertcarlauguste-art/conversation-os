# Sprint 5: Production Readiness

## Outcome

Sprint 5 prepares ConversationOS to move from a single-user local application
to a secure, observable service. Work is delivered in vertical slices so local
development remains usable while production controls are introduced.

## Milestone 1: Authentication foundation

- Clerk is the external identity provider for the Next.js and FastAPI apps.
- Health and version endpoints remain public for operations.
- Every `/api/v1` business route now crosses a shared authentication boundary.
- Domain slices receive a vendor-neutral `Principal`; Clerk-specific details do
  not leak into repositories or services.
- The frontend API transport automatically attaches a Clerk bearer token to
  fetch and upload requests.
- The navigation displays sign-in and account controls when Clerk is configured.
- Local demo mode remains available with a clearly marked development identity.
- Enabling authentication without verification keys fails during startup.
- Authorized frontend origins are explicit to prevent token reuse from an
  unexpected party.

## Configuration

Local development defaults to `AUTH_ENABLED=false`. To enable Clerk, provide
`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` to the frontend and set `AUTH_ENABLED=true`
with either `CLERK_SECRET_KEY` or the recommended `CLERK_JWT_KEY` on the backend.
Production deployments must also set `CLERK_AUTHORIZED_PARTIES` to their exact
frontend origins.

## Verification

- Backend tests: 87 passed.
- Ruff: passed.
- Black: passed.
- MyPy: passed.
- Frontend interaction tests: 3 passed.
- TypeScript: passed.
- ESLint: passed.
- Next.js production build: passed.
- Frontend dependency audit: 0 vulnerabilities.

## Milestone 2: Record ownership and tenant isolation

- Conversations and clients carry an indexed, required `owner_id`.
- New uploads and reconciled clients inherit the authenticated user's identity.
- Client identity matching is owner-scoped, so two users may independently have
  a client with the same name and role.
- Conversation and client lookups return not-found for another user's records.
- Memories, transcripts, and action items are scoped through their parent
  conversation rather than duplicating ownership on every extracted row.
- Follow-up history and every dashboard aggregate are owner-scoped.
- Manual conversation linking requires both records to belong to the caller.
- Migration `0007` preserves existing local records under `dev_user` and adds
  indexes for tenant-filtered queries.
- Dedicated isolation tests verify that repositories cannot read or match
  another owner's records.

Authentication and database authorization now work together. Before enabling
Clerk for an existing installation, an administrator must explicitly transfer
the legacy `dev_user` records to the intended Clerk user; the migration does not
guess ownership.

## Milestone 3: Production runtime and resilient processing

- Upload persistence is separated from AI processing through a job boundary.
- Local development defaults to inline processing for a simple one-command
  workflow; production is required to use the Redis queue.
- A dedicated ARQ worker executes conversation processing outside the web
  request and retries failures up to the configured limit with increasing
  backoff.
- Conversation ID job keys prevent duplicate queue submissions.
- The worker receives the authenticated owner ID so tenant isolation remains
  intact outside the request context.
- `/health` is a lightweight liveness check, while `/ready` verifies PostgreSQL
  and, in queue mode, Redis plus the worker heartbeat.
- The production container no longer enables code reload. Docker Compose keeps
  reload for local development and runs the worker as a separate service.
- Production configuration fails closed unless authentication and queued
  processing are enabled and CORS uses non-localhost origins.
- Retry count, timeout, processing mode, and CORS origins are environment-driven.

## Milestone 4: Bounded collections and processing observability

- Conversation and client endpoints support bounded `limit`/`offset`
  pagination with a maximum page size of 100.
- Conversations can be searched by title or filename and filtered by processing
  status.
- Clients can be searched by name, email, or phone and filtered by normalized
  role.
- Every filter remains owner-scoped at the repository boundary.
- The frontend provides responsive search, status/role filters, and previous/next
  pagination controls while retaining TanStack Query caching.
- Queue submissions now move conversations into the existing `QUEUED` state.
- Migration `0008` adds processing attempt count, latest error, start time, and
  completion time to conversations.
- The worker records every attempt and exposes permanent failure details through
  the conversation API and detail screen.
- Conversation detail polling now includes the queued state.

## Milestone 5: Operational status and staging gate

- Authenticated `GET /api/v1/operations` reports owner-scoped processing totals,
  retry exhaustion, and average completed processing duration.
- Queue deployments also report shared ARQ queue depth and worker-heartbeat
  availability; inline development marks those fields as not applicable.
- Deterministic alerts rank worker outage, queue backlog, exhausted retries, and
  ordinary processing failures by severity.
- `OPERATIONS_QUEUE_ALERT_THRESHOLD` makes backlog sensitivity environment-driven.
- Authentication now places the resolved user ID on request state for structured
  request logging without exposing Clerk inside domain slices.
- The staging checklist covers deployment, authentication, tenant isolation,
  queue behavior, controlled retry failure, readiness, operational alerts, and
  rollback evidence.

## Remaining staging gate

The code and checklist are ready for staging. A real end-to-end staging run still
requires a deployed staging URL plus dedicated Clerk and AI provider credentials;
those secrets must not be simulated or committed to the repository.
