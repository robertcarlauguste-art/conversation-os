# Processing visibility (Sprint 7 Milestone 1)

No migration is required. Details reuse processing_attempts, processing_started_at,
processing_completed_at, and processing_error. Failed records without a conversation
error fall back to the existing transcript error_message (queried without transcript text).
Only fixed, allowlisted diagnostic messages reach these API fields; unknown and legacy
provider errors become a generic configuration/worker diagnostic. Provider bodies are
never safe to echo, even after pattern redaction.

Queued/received time is an approximation using created_at: no queue timestamp exists.
Inline jobs were received rather than queued. Started and terminal time describe the
latest attempt; processing_completed_at is labeled Failed for failed jobs. Missing
legacy timestamps display Not recorded, rather than inventing a failure time.

A QUEUED job is possibly stalled strictly after 15 minutes from created_at. A PROCESSING
job uses the latest processing_started_at, falling back to created_at for legacy rows.
The threshold is max(900, processing_job_timeout_seconds + 60) seconds, so a configured
worker timeout always has a one-minute grace period. Fresh attempts on old uploads
are not stale. Terminal and UPLOADED records are never stale. All comparisons use UTC.

This is an age-based suspicion, not proof of abandonment: there is no per-job heartbeat.
No automatic retry or state mutation occurs. Inspect worker availability before recovery.
List/detail responses expose is_stale and stale_threshold_seconds; dashboard overview
and operations metrics expose stale counts. Counts remain owner-scoped and use all
records, whereas the conversation list is paginated. Stale is a subset of queued and
processing, not an additional status. Reload list/dashboard to refresh their counts;
conversation details continue polling while work is pending.

Diagnostics do not include audio, transcript text, authorization headers, or arbitrary
exception bodies. Existing authenticated transcript viewing remains unchanged.
Retries/recovery, historical attempt events, and heartbeat-based abandonment detection
are outside this slice.

## Final review clarifications

ConversationService owns the detail projection and transcript-error fallback. The API
never reaches into its repository. The lookup selects one row, ordered by updated_at,
created_at, then id descending, so even legacy duplicates cannot cause MultipleResultsFound.
It uses the newest transcript row, including a null error (older failures are not resurrected).

Naive stored timestamps and naive observation clocks are interpreted as UTC; offset-aware
values are converted to UTC before subtraction. The boundary is strictly greater than
the threshold. Database columns remain timezone-aware; no migration is needed.

New failures carry fixed stage diagnostics (transcription, extraction, reconciliation).
Raw JSON/parser/validation errors and worker setup/rollback/persistence exceptions are
contained before they reach worker logging. Extraction logs omit extracted names and
provider content; upload/transcription logs omit filenames. Detailed provider failure
bodies are intentionally unavailable. Existing authenticated transcript viewing is separate
from these diagnostics. No hosted smoke test or third-party SDK debug-logging audit has
been performed by this local validation.

Upload storage failures also raise fixed diagnostics, while upload-validation responses
retain their existing user-facing messages. Inline startup failures are distinguished
from queue failures; failure saving a completed result points to database availability.

## Local validation

Final review: complete `pytest -v` suite: 151 passed, 0 failed, 0 skipped.
Existing Alembic migrations were applied to a disposable PostgreSQL database, which
was removed afterward. No schema migration was added.

CI commands `ruff check app tests`, `black --check app tests` (132 files), and
`mypy app` (90 source files) all passed. Frontend `npm test` passed all 7 tests
in 2 files; `npm run typecheck`, `npm run lint`, and `npm run build` passed.

These were local Windows runs with Python 3.14.5 and Node 24.18.0. CI uses Linux,
Python 3.13, and Node 22; the CI environment itself and hosted deployment were not run.
## Hosted verification

Completed September 7, 2026 against the Railway staging environment.

The backend API, worker, and frontend deployed successfully. A new authenticated
recording completed in one processing attempt. It was received at 5:51:46 AM,
started processing at 5:51:47 AM, and completed at 5:51:53 AM. The deployed
conversation detail page displayed the attempt count and all processing timestamps.

The frontend deployment was initially skipped because its Railway watch pattern
used `/**`. The pattern was corrected to `/frontend/**` so future frontend changes
trigger deployment automatically.

## Safe retry and recovery (Sprint 7 Milestone 2)

`POST /api/v1/conversations/{id}/retry` uses the existing authenticated principal
(development identity only when authentication is disabled). It returns the queued
detail on success, 404 for absent or other-owner IDs, 409 for every state except
FAILED, and a fixed 503 diagnostic for dispatch/persistence failures. Retry always
requires Redis and a worker, including installations using inline uploads.

A PostgreSQL row lock serializes the owner-scoped FAILED check and transition to
QUEUED. The lock covers dispatch (limited to 10 seconds) and commit. Processing error
and terminal timestamp are cleared; ID, created time, storage path, previous start
time, client link, transcripts, and cumulative processing_attempts are preserved.
The worker increments attempts when work starts. A safe retry event logs only the
conversation ID and existing attempt count. There is no separate durable event-history
table: existing counts and latest-attempt fields remain the persisted history.

Each accepted dispatch uses a fresh ARQ ID, avoiding retained results from the previous
job. Its first delivery takes the same row lock and verifies QUEUED plus the expected
attempt count before entering the pipeline. The lock lasts until the attempt increment
commits. Concurrent requests return one success and one conflict; duplicate or rolled-back
deliveries do no processing. If an ambiguous dispatch is followed by another accepted
retry before either job starts, either delivery can consume the queued attempt baseline;
the other becomes a no-op. This prevents concurrent processing without a schema change.

PostgreSQL and Redis are not a distributed transaction. Dispatch/commit errors roll back
when possible; clients refresh after uncertain failures. Redis loss after database commit,
database unavailability, or process termination can still leave a queued/processing record
requiring operator recovery. This is not an outbox or guaranteed delivery mechanism.

Automatic worker backoff now keeps status PROCESSING and leaves terminal time empty.
Only exhausted attempts become FAILED; manual retry cannot overlap automatic backoff.
Setup/configuration failures become terminal without incrementing attempts. Once setup
succeeds, each manually dispatched job receives the configured automatic retry budget, while the
conversation attempt count stays cumulative. Existing Sprint 6 transcription persistence
reuses a failed transcript row and reuses completed text without calling transcription
again. Extraction and reconciliation still run under their existing behavior; this slice
does not promise exactly-once downstream side effects after partial failures.

Failed details show Retry, disable it during submission, use fixed errors, and seed the
queued detail on success. Conversation polling resumes at three seconds. Related queries
are invalidated, and memory/transcript queries include status so a recovered result is
fetched when processing completes. The original created_at remains the received/queued
approximation: an old recording freshly retried may immediately show a queued stale
warning. That warning is suspicion only, not a reason to dispatch another job.

### Administrative recovery of legacy stuck records

Use privileged database access, not a public administrative API. Before deploying this
change, drain/stop old workers: old code can expose FAILED during automatic backoff.
For a specific stuck record, pause new dispatch, stop workers, and establish that no
active, deferred, or queued ARQ job can process that conversation. Remove only its
confirmed abandoned jobs using the queue tooling; do not flush Redis or reset attempts.
An age warning alone is insufficient evidence of abandonment.

With that prerequisite satisfied, use a transaction and explicit conversation ID and
owner ID to inspect only status/attempt/timestamp metadata under `SELECT ... FOR UPDATE`.
Then perform the following parameterized update (bind values; do not paste secrets):

```sql
UPDATE conversations
SET status = 'FAILED',
    processing_error = 'Processing failed. Check provider configuration and worker availability.',
    processing_completed_at = CURRENT_TIMESTAMP,
    updated_at = CURRENT_TIMESTAMP
WHERE id = :conversation_id AND owner_id = :owner_id
  AND status IN ('QUEUED', 'PROCESSING')
RETURNING id, status, processing_attempts;
```

Require exactly one returned row; otherwise roll back and investigate. Commit, restart
updated workers and dispatch, then have the owner use Retry and observe completion or a
safe terminal error. Never change storage_path, transcript rows, or attempt counts for
this recovery. Record the ID, operator, time, and reason in the operational incident
record without audio, transcript content, credentials, or provider bodies. This manual
runbook has not been rehearsed against hosted staging in this change.


### Milestone 2 local validation

Final complete backend suite: **174 passed, 0 failed, 0 skipped** (23 additional tests).
Final complete frontend suite: **19 passed, 0 failed, 0 skipped in 4 files** (12 additional
tests). Ruff passed; Black --check passed for **133 files**; MyPy passed for **90 source
files**. TypeScript, ESLint, and the production Next.js build passed (5 static pages).
`git diff --check` passed. Final diff review covered tracked changes and new test/UI files.

Backend integration tests used a disposable local PostgreSQL database with all existing
Alembic migrations applied. Queue calls and providers were faked; concurrency tests used
independent real database sessions. Worker integration covered completed/failed transcript
reuse, duplicate first delivery, success, automatic backoff, exhaustion, and setup failure.
No migration or commit was created. Hosted staging and a live Redis/ARQ end-to-end retry
were not exercised. Deploy API and worker together after draining old worker jobs.
