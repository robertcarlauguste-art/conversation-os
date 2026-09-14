# Tenant Isolation & Authorization Security

## Pre-change inventory — 2026-09-14

Base: `e818ad7` (PR #13, configuration validation), isolated branch
`launch/tenant-isolation`. The original checkout, including retry tests and
processing-visibility notes, is untouched. No deployment is part of this change.

The tenant boundary is Clerk's verified `sub` / `Principal.user_id`, stored as
`owner_id` on conversations and clients. `organization_id` is informational;
there is no organization sharing or administrator role in this application.
All 21 business operations below are mounted under `/api/v1` with
`require_principal`. Request parameters never determine the authenticated owner.
Development auth bypass is prohibited by hosted configuration validation.

| Method and path (under /api/v1) | Authorization and persistence trace |
| --- | --- |
| GET /auth/me | Verified principal only; no resource lookup. |
| POST /conversations | Upload service assigns repository owner; server generates storage key; queue receives principal owner or inline orchestrator is constructed with it. |
| GET /conversations | Repository owner predicate applies before search (title/filename), status, ordering and pagination. |
| GET /conversations/{id} | Owner-scoped repository lookup; processing metadata and fallback transcript error use the same owner. Response omits storage path. |
| DELETE /conversations/{id} | Owner lookup before storage delete; database delete also has owner predicate; result children cascade. |
| POST /conversations/{id}/retry | Owner-scoped row lock before status check, mutation and enqueue; enqueue owner comes from principal. Foreign and missing IDs return 404. |
| GET /clients | Owner filter before name/email/phone search, role and pagination. Related collections are eagerly loaded. |
| GET /clients/{id} | Owner-scoped parent lookup; facts, people and conversations loaded by relationships. |
| GET /clients/{id}/conversations | Owner-scoped client check followed by owner-scoped conversation query. |
| POST /clients/{client_id}/conversations/{conversation_id} | Both client and conversation checked under authenticated owner before link commit. |
| DELETE /clients/{client_id}/conversations/{conversation_id} | Conversation owner checked, then link equality; parent client not independently checked. |
| GET /transcriptions/by-conversation/{id} | Transcript joined to conversation with owner predicate. Includes text and sanitized processing error. |
| GET /memories | Join to owned conversation; includes summaries and related memory content. |
| GET /memories/by-conversation/{id} | Same owner join. |
| GET /memories/{id} | Same owner join. |
| POST /memories/action-items/{id}/complete | Action → memory → owned conversation lookup before mutation. |
| POST /memories/action-items/{id}/reopen | Same lookup before mutation. |
| GET /dashboard | Scoped conversation/client services; follow-up actions joined to owned clients; action items joined to owned conversations. Client outer joins lack their own owner predicate. |
| POST /dashboard/briefing | Same dashboard data becomes provider prompt or deterministic fallback; no separate global data source/cache. |
| POST /dashboard/recommendations/{client_id}/actions | Service checks owned client before inserting follow-up; handler does not translate ClientNotFoundError to 404. |
| GET /operations | SQL aggregates scoped to conversation owner, BUT shared Redis queue depth and worker health are returned to any signed-in user. No admin authorization exists. |

Public surface: GET `/health`, `/ready`, `/version`, OpenAPI and documentation.
Readiness reports coarse dependency availability only; it contains no resource IDs,
counts, queue contents, storage keys or exception details. Documentation describes
schemas, not tenant records. No other routers, static storage mounts, frontend
server API handlers, webhooks or background-job HTTP endpoints were found.

## Internal writes and storage boundaries

- Worker payload contains conversation ID and owner. Retry first delivery checks
  the owner-scoped locked row; orchestrator checks ownership before storage reads,
  transcription, memory extraction and reconciliation. Terminal failure updates
  are owner-scoped. Redis is a trusted backend channel, not a user API.
- Transcription persists/reuses a result for the authorized conversation. Memory
  creation persists summary, decisions, action items and people. These internal
  services rely on the orchestrator's prior authorization; they are not HTTP APIs.
- Client reconciliation matches name/role only within owner and stamps owner on
  new clients. Fact provenance, person-client linking and conversation-client
  updates rely on caller-supplied IDs. Person linking currently uses unscoped
  `session.get`; these write helpers need explicit same-owner validation.
- BaseRepository is a trusted persistence primitive, not an authorization API.
  TranscriptRepository inherits an unscoped direct `get`, although no current
  handler uses it. This should be scoped for future-safe internal access.
- Local and S3 storage accept backend paths, not user-supplied URLs. Upload creates
  a random key. S3 validates bucket/prefix; local legacy absolute paths are trusted
  stored data. No audio download, presign, finalize, object listing, client create,
  client edit/delete, transcript edit, or raw job/status routes exist. The API never
  emits audio object URLs. Bucket public-access settings require hosted verification.

## Findings before implementation

1. Confirmed metadata exposure: `/operations` reveals shared queue depth. Keep
   user-scoped processing metrics but withhold infrastructure metrics from this
   tenant endpoint; do not invent an administrator role.
2. Error semantics defect: foreign/missing dashboard follow-up client produces an
   unhandled exception rather than the project's 404 response.
3. Defense-in-depth gaps: internal linking/provenance helpers and eager related
   loads can cross boundaries if passed inconsistent IDs. Harden both write checks
   and related-data reads; exercise deliberately inconsistent test rows as well as
   normal independent tenants. These are not claimed as demonstrated public IDORs.
4. Existing isolation tests cover only four repository scenarios, not the complete
   HTTP surface, operations, worker/storage boundaries, or both attack directions.

Automated local failure fixtures do not constitute or replace Sprint 7's pending
hosted genuine-failure retry smoke test.

Frontend follow-through found a further defect: the root QueryClient survives
Clerk account/session changes while query keys do not include identity. Cached
tenant responses could be displayed after an account switch in the same page
lifetime. Partition the entire query/mutation cache by verified user and session,
and install the token provider before mounting data-fetching children.

## Implemented changes and evidence

- `/operations` no longer reads Redis. Nullable infrastructure fields remain null,
  preserving the response schema; unavailable infrastructure is not fabricated into
  a worker-down alert. Only owner-scoped processing alerts are returned. No role or
  privileged bypass was introduced.
- Dashboard follow-up handlers translate missing/foreign clients to 404. Unlink
  now checks the parent client independently before checking the conversation.
- Transcript direct-ID reads are owner-scoped. Person/client links, conversation/
  client updates and client-fact provenance validate the authenticated owner on
  both sides. Client related collections and dashboard client joins are scoped.
- Frontend query/mutation caches remount for each user/session pair. The token
  bridge is ready before data-fetching children mount. Old requests cannot populate
  the new session's cache.

Final verification on September 14, 2026:

| Check | Result |
| --- | --- |
| PostgreSQL migrations on disposable pgvector PostgreSQL 16 | All migrations through 0008 applied. |
| Full backend suite, built Linux Python 3.13 image | **258 passed, 0 failed, 0 errors, 0 skipped**, 25.88 seconds. |
| Earlier Windows Python 3.14 full suite, before four additional coverage cases | 254 passed, 106.10 seconds. |
| New security suite | 24 parameterized cases, included in the final full suite. |
| Backend Ruff | Passed. |
| Backend Black | Passed, 135 files. |
| Backend MyPy | Passed, 90 source files. |
| Frontend Vitest | **39 passed across 6 files**, including the session-cache regression. |
| Frontend ESLint and TypeScript | Passed. No separate frontend formatter is configured. |
| Frontend production build | Passed with `APP_ENV=test`; hosted keys were not used. |
| Backend Docker build | Passed, local `conversation-os-tenant-security:local` image; not published. |
| Diff whitespace check | Passed. |

Regression effectiveness was verified against an untouched `e818ad7` copy:
eight selected backend cases fail (two directions each for dashboard 404 semantics,
shared Redis access, unscoped transcript direct reads and inconsistent related data).
The browser cache test also fails on the old code by visibly retaining
`private_alpha` after switching to beta. These same cases pass on the fixed code.

The HTTP tests retain the real FastAPI authentication dependency, handlers,
services and PostgreSQL queries. Only Clerk's external verification response,
provider calls, storage and enqueue edges are replaced. The two verified subjects
deliberately share an organization and carry org-admin claims to confirm these
claims do not broaden the user-owned boundary. All 21 registered business
operations are enumerated and tested with missing, invalid and forged-admin tokens.

Coverage includes successful owned reads/writes as controls; cross-tenant and
missing-ID response equivalence; all nested link combinations; search, filters,
pagination and wildcards; transcripts, summaries, actions, client facts and people;
dashboard and provider-prompt isolation; operations noninterference when the other
tenant changes processing state; upload owner spoofing; absent object/job routes;
worker owner mismatch without storage/provider access; and browser account/session
changes, sign-out and late responses. Local synthetic failed records exercise retry
authorization without manufacturing a hosted failure.

## Remaining boundaries and release gate

- Real Clerk signature/session behavior, two hosted browser accounts, R2 public
  access/custom domains, CDN/proxy behavior, and hosted worker execution require
  the separate staging procedure. Automated fake external edges do not prove these.
- Authorization is at application query/service boundaries, not PostgreSQL RLS.
  Database administrators, backend storage credentials and Redis publishers remain
  trusted. Low-level persistence and extraction/transcription inputs are internal
  orchestration interfaces, not safe arbitrary-user APIs. New callers must retain
  the owner-scoped orchestration gate; new public routes require isolation tests.
- No organization sharing, application administrator role, direct object download,
  finalize/presign API or client-delete API exists. Adding one changes this inventory.
- PR #13 was reported open at the supplied checkpoint; no merge, push, PR change,
  staging deployment or hosted data mutation was performed. Both milestones must
  remain present when the eventual reviewed release is assembled.
- The security milestone is **not signed off for launch** until hosted checks pass.
  The genuine-failure hosted retry smoke remains pending independently.

See `docs/deployment/tenant-isolation-staging.md` for the exact proposed release,
two-account smoke, evidence collection and rollback procedure.
