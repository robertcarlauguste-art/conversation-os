# Sprint 7: Operational Readiness and Recovery

## Objective

Turn the functioning ConversationOS staging deployment into a reliable, observable, and recoverable system suitable for a small external usability test.

Sprint 7 does not add major product features. It focuses on detecting failures, recovering safely, protecting data, and proving that the team can operate the system without inspecting raw infrastructure logs.

## Starting baseline

- Railway hosts the frontend, backend API, worker, PostgreSQL, and Redis.
- Cloudflare R2 stores recordings in a private staging bucket.
- Clerk protects authenticated application access.
- Authenticated recordings can complete the full hosted workflow.
- Exhausted worker jobs persist `FAILED` status instead of remaining stuck.
- Backend tests, formatting, linting, and GitHub checks pass.
- Backend changes automatically deploy the API and worker.

## Milestone 1: Processing visibility

- Display processing attempt count and the latest safe error message.
- Show when a conversation was queued, started, completed, or failed.
- Add dashboard counts for queued, processing, completed, and failed records.
- Identify conversations that remain queued or processing beyond a defined threshold.
- Keep secrets, authorization headers, raw audio, and full transcripts out of logs.

### Acceptance criteria

- An operator can understand a failed job without opening Railway logs.
- Stuck-job detection distinguishes active work from abandoned work.
- Dashboard counts agree with the conversation list.

## Milestone 2: Safe retry and recovery

- Add an authenticated retry action for failed conversations.
- Reject retries for conversations already queued or processing.
- Reuse the stored recording and existing transcript safely.
- Reset terminal error state when a retry begins.
- Prevent duplicate transcript rows and concurrent duplicate jobs.
- Add an administrative recovery path for legacy records stuck in processing.
- Record retry events and attempt counts.

### Acceptance criteria

- A failed conversation can be retried from the application.
- Repeated clicks do not create duplicate jobs or transcripts.
- A successful retry ends in `COMPLETED`.
- An exhausted retry ends in `FAILED` with a useful error message.
- Regression tests cover retry authorization, idempotency, and rollback behavior.

## Milestone 3: Configuration and secret safety

- Validate required production variables during service startup.
- Reject secrets containing leading or trailing whitespace or line breaks.
- Report configuration failures using variable names without exposing values.
- Document rotation procedures for Clerk, Anthropic, and R2 credentials.
- Confirm retired credentials are revoked.
- Verify backend and worker use the same R2 configuration.

### Acceptance criteria

- A malformed secret prevents an unhealthy deployment from becoming active.
- No secret value appears in application logs or user-facing errors.
- Credential rotation can be completed without losing stored recordings.

## Milestone 4: Security and recovery rehearsal

- Verify two independent Clerk users cannot access each other’s conversations or clients.
- Confirm direct-ID requests return not-found for records owned by another user.
- Rehearse application rollback to the previous known-good Railway deployment.
- Rehearse PostgreSQL backup and restore using staging-safe data.
- Confirm restored records still reference readable private R2 objects.
- Record recovery steps and expected completion times.

### Acceptance criteria

- Cross-tenant access tests pass at the API and application levels.
- A rollback is completed and reversed successfully.
- A database backup is restored and validated.
- Recovery documentation is usable without relying on chat history.

## Milestone 5: External-demo gate

- Run the staging smoke test after all operational changes.
- Upload and process a new non-sensitive recording.
- Exercise one controlled failure and successful retry.
- Conduct a short Realtor usability session.
- Record confusing behavior, missing information, and priority improvements.
- Remove test data that is no longer needed.

### Exit criteria

- Automated checks pass.
- Staging health checks are green.
- A new recording reaches `COMPLETED`.
- A controlled failed recording is retried successfully.
- Cross-tenant isolation is verified.
- Rollback and restore procedures are documented and rehearsed.
- No active or logged secret is known to be exposed.
- Usability findings are captured for product prioritization.

## Suggested implementation order

1. Processing timestamps, safe errors, and stuck-job detection.
2. Failed-conversation retry API and UI.
3. Configuration whitespace validation.
4. Cross-tenant automated tests.
5. Monitoring and alerts.
6. Rollback and database-restore rehearsal.
7. External usability session.

## Out of scope

- Production launch.
- Public registration or broad customer onboarding.
- Billing and subscription management.
- Large-scale analytics.
- Major redesign of the dashboard or conversation experience.
- Long-term production retention policies.