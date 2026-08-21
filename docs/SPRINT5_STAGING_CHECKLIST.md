# Sprint 5 staging validation checklist

Use this checklist on a non-production deployment with a dedicated Clerk
application, database, Redis instance, object storage directory, and AI API keys.
Do not reuse development data or production credentials.

## Required configuration

- `APP_ENV=production`
- `AUTH_ENABLED=true`
- `CLERK_SECRET_KEY` or `CLERK_JWT_KEY`
- `CLERK_AUTHORIZED_PARTIES` set to the exact staging frontend origin
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
- `PROCESSING_MODE=queue`
- `DATABASE_URL` and `REDIS_URL` for staging services
- `CORS_ORIGINS` containing only the staging frontend origin
- `ANTHROPIC_API_KEY` and, when transcription is enabled, `OPENAI_API_KEY`
- A deliberate `OPERATIONS_QUEUE_ALERT_THRESHOLD` for staging load

## Deployment

- Apply every Alembic migration through `0008` before starting application traffic.
- Start the API and worker as separate processes from the same release image.
- Confirm `/health` returns HTTP 200.
- Confirm `/ready` returns HTTP 200 with database, Redis, and worker all `ok`.
- Run `scripts/staging-smoke.ps1 -BaseUrl <api-url> -BearerToken <token>` and
  confirm all four smoke checks pass. The script does not print the token.

## Authentication and isolation

- Confirm a signed-out request to `/api/v1/auth/me` returns HTTP 401.
- Sign in as user A and create a conversation and client.
- Sign in as user B and confirm user A's records do not appear in lists, search,
  detail routes, dashboard data, or `/api/v1/operations` processing totals.
- Confirm user B receives not-found when directly requesting user A's record IDs.

## Processing workflow

- Upload a supported audio file and confirm the state moves from `QUEUED` to
  `PROCESSING` to `COMPLETED` without blocking the upload request.
- Confirm transcription, memories, action items, and client reconciliation are
  attached to the authenticated owner.
- Trigger a controlled provider failure and confirm attempts increase, retries
  use backoff, and the final failure records a useful error.
- Confirm an exhausted failure creates a `retry_exhausted` operational alert.

## Operational status

- Call authenticated `GET /api/v1/operations` and verify account-scoped totals,
  average processing duration, queue depth, worker availability, and timestamp.
- Stop the worker and verify `/ready` returns HTTP 503 and operations reports a
  critical `worker_unavailable` alert; then restart it and verify recovery.
- Add enough test jobs to meet the configured threshold and verify the
  `queue_backlog` alert, then drain the queue and verify it clears.

## Release decision and rollback

- Preserve API, worker, and browser logs for the test window.
- Record the deployed commit and migration revision.
- Do not approve production until every item above passes.
- Roll back application processes to the previous image if needed. Database
  downgrade requires a separately reviewed plan because migrations may contain
  user data.
