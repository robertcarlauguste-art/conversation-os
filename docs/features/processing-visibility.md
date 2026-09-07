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
