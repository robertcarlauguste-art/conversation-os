# Sprint 6: Cloud Staging and Durable Storage

## Goal

Move ConversationOS from a single-machine staging environment to a repeatable,
private cloud-staging deployment that can support controlled external demos.
The product must preserve the authenticated tenant boundary and resilient worker
pipeline proven in Sprint 5.

Sprint 6 is complete only when a recording uploaded through the cloud frontend
is stored privately, processed by a separate worker, and visible only to the
authenticated owner.

## Entry conditions

- Sprint 5 is merged and local credentialed staging has passed.
- Clerk authentication, PostgreSQL, Redis/ARQ, and the API/worker separation are
  already operational.
- Local upload storage remains the development default.
- Cloudflare R2 Standard is approved for private S3-compatible staging storage.
- No application deployment target has been selected yet.

## Architecture decision

The API and worker must use the same storage factory. Neither process may
construct `LocalStorageBackend` directly. The factory will select a provider
from centralized configuration and return the existing `StorageBackend`
contract.

Stored locations must be self-describing:

- New local objects use a local storage location.
- Cloud objects use a private S3-compatible bucket and object key.
- Legacy absolute local paths remain readable during migration.

Business services continue to call only `save`, `read`, and `delete`; provider
credentials, endpoint URLs, buckets, and object-key rules remain infrastructure
concerns.

## Milestone 1: Shared storage provider boundary

Status: complete and locally verified.

- Add `STORAGE_BACKEND=local|s3` with `local` as the development default.
- Add one shared `build_storage_backend(settings)` factory.
- Use the factory in both FastAPI dependencies and the ARQ worker.
- Remove direct worker construction of `LocalStorageBackend`.
- Define canonical storage locations without exposing original filenames.
- Preserve reads and deletes for existing absolute local paths.
- Fail closed when S3 mode lacks endpoint, region, bucket, or credentials.
- Add contract tests that every backend implements the same save/read/delete
  behavior and that API and worker receive the same configured provider.

## Milestone 2: Private S3-compatible storage

Provider decision: Cloudflare R2 Standard, using a private staging bucket and
bucket-scoped S3 credentials. The implementation remains portable through the
generic S3 API and does not expose R2-specific behavior to business services.

Status: complete and verified against the private `conversation-os-staging`
bucket. A real authenticated upload was stored in R2, processed by the separate
worker in one attempt, and deleted through the application. The database row
and private object were both removed, while legacy local records remained.

- Implement `S3StorageBackend` behind the existing interface.
- Generate opaque object keys under a conversations prefix.
- Keep the bucket private; do not return public object URLs.
- Enable provider-supported encryption at rest.
- Restrict credentials to object read/write/delete for the staging bucket.
- Preserve current file-size, extension, and MIME validation before upload.
- Delete the stored object when a conversation is deleted.
- Log bucket-independent object identifiers, never access keys or signed URLs.
- Test upload, read, missing-object delete, provider failure, and path-routing
  behavior without contacting a real cloud provider in CI.

## Milestone 3: Repeatable cloud staging

Provider decision: Railway for the Next.js frontend, FastAPI API, ARQ worker,
PostgreSQL, and Redis; Cloudflare R2 remains the private object store. Deployment
configuration is prepared before any Railway project resources are created.

- Select the deployment target only after comparing support for the Next.js
  frontend, FastAPI API, independent ARQ worker, PostgreSQL, Redis, private
  secrets, health checks, and an S3-compatible storage service.
- Add deployment manifests or infrastructure-as-code under `infrastructure/`.
- Run Alembic migrations as an explicit release step before application traffic.
- Configure exact Clerk authorized parties and CORS origins for staging.
- Keep API and worker on the same release image and database revision.
- Require `/health` for liveness and `/ready` for release readiness.
- Document secret rotation, deploy, rollback, and database restore procedures.

## Milestone 4: Observability and external-demo gate

- Send structured API and worker logs to one searchable destination.
- Add error reporting for failed requests and exhausted processing jobs.
- Record queue depth, worker heartbeat, processing duration, and failure alerts.
- Run the staging smoke checker against the deployed URL.
- Verify two independent Clerk users cannot access each other's records.
- Exercise worker outage/recovery and controlled retry exhaustion.
- Upload and process a non-sensitive real recording end to end.
- Complete a short Realtor usability session and record findings before opening
  the environment to additional users.

## Security requirements

- Never commit Clerk, AI, database, Redis, or object-storage credentials.
- Use a dedicated staging bucket and dedicated least-privilege credentials.
- Do not expose audio through public URLs.
- Do not log bearer tokens, secrets, raw audio, or full transcripts.
- Keep staging data separate from local development and future production data.
- Define retention and deletion behavior before accepting real client recordings.

## Verification gate

- Backend tests, Ruff, Black, and MyPy pass.
- Frontend interaction tests, TypeScript, ESLint, build, and dependency audit pass.
- Storage contract tests pass for local and fake S3 providers.
- Clean migrations pass against a new staging database.
- Cloud `/ready` reports database, Redis, and worker as healthy.
- Authenticated upload reaches `COMPLETED` through the separate worker.
- The stored object is private and deleted with its conversation.
- Cross-tenant direct-ID requests return not-found.
- Rollback steps are documented and rehearsed.

## Decision gates

Before Milestone 2 implementation, select the S3-compatible storage provider.
Before Milestone 3 implementation, select the application hosting, PostgreSQL,
Redis, logging, and error-reporting providers. These choices create external
resources and possible cost, so they require explicit approval.

## First implementation slice

Build the shared storage factory, canonical location format, legacy local-path
compatibility, configuration validation, and tests. This slice is provider-safe:
it improves architecture without creating accounts, spending money, or changing
the local development default.
## Staging completion record

Date: September 6, 2026

Sprint 6 delivered a functioning ConversationOS staging environment on Railway:

- Next.js frontend, FastAPI API, ARQ worker, PostgreSQL, and Redis are deployed.
- Cloudflare R2 provides private S3-compatible recording storage.
- Clerk authentication and staging access controls are active.
- An authenticated recording completed the full upload, storage, queue, transcription, and persistence workflow.
- Worker retries now roll back failed database transactions, reuse existing transcript rows, and persist terminal `FAILED` status instead of leaving jobs stuck in `PROCESSING`.
- Railway watch paths now trigger both backend-api and worker deployments for changes under `/backend`.
- The full backend test suite passes with 118 tests.
- Ruff, Black, and GitHub CI checks pass.

During staging verification, Clerk, R2, and Anthropic credentials were rotated and corrected. Secret values must remain outside source control and must not appear in screenshots or logs.

The core staging deployment and durable-storage objectives are complete. Remaining external-demo hardening—centralized error reporting, alerts, cross-tenant verification, rollback rehearsal, database restore rehearsal, and the Realtor usability session—will continue in Sprint 7.