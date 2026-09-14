# Sprint 7 Milestone 3: Configuration Validation

## Process inventory and startup boundary

| Process/service | Entry point | Configuration validation |
| --- | --- | --- |
| FastAPI API | `uvicorn app.main:app` | Cached `app.core.config.get_settings()` runs during import, before database/client construction and traffic |
| ARQ worker | `arq app.processing.worker.WorkerSettings` | Same settings loader, before Redis worker construction |
| Database release job | `alembic upgrade head` | Same loader before engine creation; uses the API service's full environment |
| Next.js frontend | `next dev`, `next build`, `next start` | `next.config.ts` calls `environment.ts`; server secret required only at runtime |
| PostgreSQL + pgvector | Image-managed server | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` in Compose; hosted provider manages these. Application validates the resulting `DATABASE_URL` |
| Redis | Image-managed server | Local image uses its defaults; application validates `REDIS_URL`. Hosted Redis authentication is supplied in that URL |
| R2, Clerk, Anthropic, OpenAI | External services, no repository process | Application validates configuration syntax and presence; hosted smoke verifies access |

Compose and Railway deploy the same three application processes. Only the API's Railway release step runs migrations. CI also invokes migrations and tests. No additional deployable application process was found in scripts, Docker, infrastructure, or workflows.

## Backend configuration contract

Environment variables are uppercase versions of fields in `backend/app/core/config.py`. API, worker, and migration job intentionally share the same full configuration contract. This prevents API/worker divergence, and makes a bad application configuration fail during the release step.

| Variables | Validation and requirements |
| --- | --- |
| `APP_ENV` | `development` (default), `test`, `staging`, or `production`; misspellings fail |
| `APP_NAME`, `VERSION`, `AUTH_DEV_USER_ID`, `STORAGE_ROOT` | Nonempty strings, no surrounding whitespace/control characters; existing defaults retained |
| `PORT` | Integer 1–65535; default 8000; Railway command consumes it |
| `DATABASE_URL` | PostgreSQL URL with user, password, host, valid port, database; `postgresql://` normalized to psycopg; asyncpg also supported. Explicit value required when hosted |
| `REDIS_URL` | `redis://` or `rediss://`, host/valid port, nonnegative database index, no unsupported query parameters; explicit value required when hosted |
| `PROCESSING_MODE` | `inline` or `queue`; hosted requires `queue` |
| `PROCESSING_MAX_TRIES` | Integer 1–10, default 3 |
| `PROCESSING_JOB_TIMEOUT_SECONDS` | Integer >=30, default 300 |
| `OPERATIONS_QUEUE_ALERT_THRESHOLD` | Integer >=1, default 25 |
| `MAX_UPLOAD_SIZE_BYTES` | Integer >=1, default 104857600 |
| `AI_REQUEST_TIMEOUT_SECONDS` | Finite number >0, default 60 |
| `CORS_ORIGINS`, `CLERK_AUTHORIZED_PARTIES` | Nonempty JSON arrays of exact HTTP(S) origins, no credentials/query/path/trailing slash. Hosted requires HTTPS and excludes localhost/loopback defaults |
| `AUTH_ENABLED` | Boolean; hosted requires true |
| `CLERK_SECRET_KEY`, `CLERK_JWT_KEY` | At least one required when auth enabled. Secret must contain no whitespace/control characters. JWT key must parse as an RSA PEM public key; PEM line breaks are supported |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | Both required when hosted; opaque non-whitespace tokens. Local development retains existing absent-key behavior |
| `ANTHROPIC_MODEL`, `OPENAI_WHISPER_MODEL` | Nonempty tokens; existing defaults retained |
| `STORAGE_BACKEND` | `local` or `s3`; hosted requires shared `s3` for separate API/worker containers |
| `S3_ENDPOINT_URL`, `S3_REGION`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | All required for s3. HTTP(S) endpoint without URL credentials/query; hosted HTTPS. Bucket 3–63 lowercase letters/digits/dots/hyphens; no adjacent dots or IP-shaped name. Region and credentials contain no whitespace |
| `ALLOWED_AUDIO_MIME_TYPES` | Nonempty JSON array of audio MIME types; existing default allowlist retained |
| `SUPABASE_URL`, `SUPABASE_KEY` | Unused scaffold, optional. If supplied, URL syntax and token whitespace are checked; never required |

Empty optional strings become absent values. Credentials are rejected rather than silently trimmed. No credential prefix or length assumptions are imposed on opaque provider/storage tokens. Validation does not call providers or prove credentials are current.

Runtime exceptions identify variables and corrective actions, suppress raw input and exception chains, and never print the settings object. Pydantic direct validation errors also hide inputs in their text. Do not log `ValidationError.errors()` or serialize settings: these programmatic objects can contain credentials.

## Frontend contract

- `APP_ENV`: same four environments; if absent, `NODE_ENV=production` selects production, otherwise development. `APP_ENV=test` explicitly supports CI builds without hosted credentials.
- `NEXT_PUBLIC_API_URL`: required when hosted; valid public HTTPS origin. Local development keeps its existing localhost fallback.
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`: required when hosted; Clerk test/live prefix and encoded hostname shape validated.
- `CLERK_SECRET_KEY`: required at runtime whenever a publishable key is supplied; test/live prefix must match. Build does not require this server secret.
- `PORT`: optional integer 1–65535, handled by Next at runtime.

Railway Docker builds default `APP_ENV=production`. Set it to `staging` for staging if desired, and keep it consistent at build/runtime. Both hosted labels enforce identical checks. `NEXT_PUBLIC_*` values are embedded at build time: changing them requires a rebuild, not merely a restart. Runtime values must match the build values; this validator does not inspect the compiled bundle for mismatches.

## Concrete staging deployment and smoke checklist

1. Review and commit the configuration changes with existing work accounted for. Keep API and worker on the same commit. Do not mark Milestone 2's hosted retry smoke complete.
2. In Railway, review backend **and worker** variables against the table above. Set both `CORS_ORIGINS` and `CLERK_AUTHORIZED_PARTIES` on both services, even though the worker does not serve HTTP. Preserve existing Clerk staging keys; `APP_ENV=production` on the existing staging services remains supported.
3. Verify both services reference the same database, Redis, R2 endpoint, region, bucket and bucket-scoped credentials. Use the service variable UI; never paste values into logs or this document.
4. Configure frontend `APP_ENV`, HTTPS backend URL, publishable key at build and runtime, and matching server secret at runtime. Rebuild the frontend for public-variable changes.
5. Deploy the API. Its `alembic upgrade head` release step validates the full backend configuration. Confirm it succeeds, then check `/health` and `/version`.
6. Deploy the worker from the same commit. Confirm it starts with no configuration errors. Deploy/rebuild the frontend and confirm sign-in and authenticated API access.
7. Require `/ready` to report database, Redis and worker healthy. Run `./scripts/staging-smoke.ps1 -BaseUrl "https://<backend-domain>" -BearerToken $env:STAGING_BEARER_TOKEN` with a current signed-in user token supplied securely in that environment variable. Upload one new non-sensitive recording; confirm it reaches `COMPLETED`, with transcript/summary and readable stored audio.
8. Verify rejection behavior in a **disposable service/environment with no queue consumers or real conversations**: run only `python -c "from app.core.config import get_settings; get_settings()"` with a missing `ANTHROPIC_API_KEY`, then a dummy whitespace-damaged key, then invalid timeout. Each must exit nonzero with variable names and no supplied values. For frontend, try a disposable build with missing public API URL, and a disposable `next start` with missing server secret. Restore correct configuration before starting any application processes. These checks do not create failed conversations.
9. If startup fails, fix the named variable and redeploy; roll back API/worker/frontend together to the prior successful commit if needed. No schema migration is introduced by this milestone.
10. Leave the **Sprint 7 Milestone 2 real-failure retry smoke test pending until a genuine failed conversation appears**. Do not force provider failures or manufacture a failed recording to close it.

## Remaining operational checks

Hosted deployment has not been performed by this change. Credentials' validity, provider/model access, storage permissions, local-directory writability, network reachability, database schema, and API/worker configuration equality require the checks above. Managed database/Redis startup settings remain owned by their images/providers. Static configuration checks do not replace `/ready`, monitoring, or recovery rehearsal.

Credential rotation/revocation in the broader Sprint 7 plan remains a separate operational task; no credentials are changed or revoked here.
