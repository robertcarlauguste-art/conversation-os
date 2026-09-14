# Operator monitoring and alerts

Status: implementation ready for review; not deployed or signed off. The user has
no alert destination yet. Delivery must remain disabled until a destination is
configured and an actual notification is received. Configuration validation and
tenant isolation are preserved in the base release `c1893cc`.

## Inventory and boundary

Existing `/health`, `/ready`, ARQ heartbeat, processing state/timestamps, safe
diagnostics and request/pipeline logs are retained. `/api/v1/operations` remains a
tenant endpoint: shared infrastructure metrics stay null. The new monitor has no
HTTP routes and runs separately using `python -m app.monitoring`.

The operator process reads aggregate database counts, Redis health/queue depth,
the worker heartbeat, public API liveness and S3 bucket availability. It does not
read transcripts, summaries, object bodies, client names or user identifiers.
The explicit cross-owner query is confined to `app/monitoring/repository.py`.

## Signals and defaults

Poll every 60 seconds. Fire after two consecutive failing observations and resolve
after two consecutive healthy observations. Unknown dependent signals reset the
consecutive counters but never resolve an already announced incident.

| Code | Condition | First response |
| --- | --- | --- |
| api_unavailable | `/health` fails, times out or returns unexpected content | Check API deployment and logs; consult rollback runbook. |
| database_unavailable | Aggregate query cannot complete within 10 seconds | Check database availability/connections; do not retry all jobs blindly. |
| redis_unavailable | Redis check fails | Check Redis service; downstream queue/worker signals become unknown. |
| worker_unavailable | Redis reachable but ARQ heartbeat missing | Check worker deployment and configuration; restart only through normal recovery process. |
| queue_backlog | ARQ sorted-set cardinality >=25 | Check worker throughput, job age and provider health. Includes scheduled retries; not an exact runnable-job count. |
| storage_unavailable | Authenticated S3 HeadBucket fails | Check R2 availability and access credentials. This does not prove object write/read permissions. Local storage is unsupported by the independent monitor. |
| processing_failed | At least one currently failed conversation | Use authorized operator investigation; distinguish old unresolved work from a new outage. |
| processing_stalled | Queued/processing work overdue >=max(900, job timeout+60) seconds | Inspect processing timestamps/worker logs. A stale flag is not proof the job is abandoned. |
| repeated_provider_failures | >=3 conversations with recent transcription/extraction error state in 15 minutes | Check provider status/configuration and recording validity. This is a provider-stage symptom, not proof of provider outage. |

Provider detection uses persisted current error state, including work still being
retried. It does not count every provider attempt and can miss transient errors
cleared before a poll. Existing safe logs remain relevant for investigation.
Stale queued work uses its last update so a retry of an old recording is not
immediately classified as overdue.

## Configuration

All settings remain centralized in `app/core/config.py`. The monitor uses existing
validated backend settings for database, Redis, processing and storage. It never
publishes secrets in output. Use the same version/configuration mode as staging;
the hosted label currently uses `APP_ENV=production` even though Railway is staging.
Set the monitor's `APP_ENV=staging` so notifications identify their destination
environment clearly; both labels retain hosted validation requirements.

| Variable | Default / requirement |
| --- | --- |
| MONITORING_API_URL | Required by monitor; HTTPS API base URL, no credentials or fragment |
| MONITORING_WEBHOOK_URL | Omitted disables delivery; HTTPS JSON receiver, treated as a secret |
| MONITORING_HEARTBEAT_URL | Optional secret HTTPS GET endpoint for an independent missing-heartbeat service |
| MONITORING_STATE_PATH | `/data/monitoring-state.json`; persistent volume required |
| MONITORING_INTERVAL_SECONDS | 60; minimum 30 |
| MONITORING_CONSECUTIVE_CHECKS | 2; minimum 1 |
| MONITORING_FAILURE_WINDOW_SECONDS | 900; minimum 60 |
| MONITORING_PROVIDER_FAILURE_THRESHOLD | 3; minimum 1 |
| OPERATIONS_QUEUE_ALERT_THRESHOLD | Existing default 25 |

Do not add a monitor route, public metrics endpoint, or frontend operator screen.
Run exactly one replica with exclusive access to its state file. Alert state is
atomically replaced and flushed. Invalid/unwritable state stops the monitor with a
fixed safe error; it is not silently reset. Keep state on restart/rollback. Do not
scale replicas without implementing coordinated delivery state.

## Delivery contract

The HTTPS receiver must accept JSON with `service`, `environment`, `code`, `status`.
Status is `firing` or `resolved`. It must return 2xx after accepting the event and
route it to the chosen operator inbox. Configure the receiver to map each
environment+code to one incident. A generic URL is not automatically compatible
with Slack/email/incident vendor APIs: configure and test an actual receiver.

No request URLs, raw exceptions, IDs, counts, credentials or customer content are
sent. Redirects are not followed. Timeout/non-2xx leaves delivery unacknowledged,
so a later poll retries. Network ambiguity or a crash after delivery but before
state persistence may duplicate an event: delivery is at least once, not exactly
once. Recovery is sent only for an announced incident. A 2xx proves receiver
acceptance, not that a human received email.

## Proposed staging rollout and acceptance

1. Review the diff and tests before merging. Main merges trigger existing Railway
   API/worker/frontend deployments, so review before merging even though those
   processes do not start the monitor. No schema migration is required.
2. Choose an operator destination, provision its receiver and verify the contract.
   Do not send tenant data or paste receiver secrets into chat.
3. Create a separate single-replica monitor service from the backend image with a
   persistent `/data` volume and start command `python -m app.monitoring`. No public
   domain is needed. Prefer read-only database and least-privilege Redis/S3 access;
   validate those permissions before replacing existing credentials.
4. Begin without MONITORING_WEBHOOK_URL and run `--once` for a read-only staging
   probe. Check signal values; no incident delivery is claimed during dry run.
5. Verify firing, deduplication, retry, restart and recovery using a disposable
   environment or dedicated test receiver. Use clearly labeled test incidents;
   never cause real staging jobs/provider failures merely to test an alert.
6. Configure an independent external uptime monitor for the API plus an independent
   missing-heartbeat check for this monitoring service. A monitor hosted alongside
   the app cannot report its own complete host/network outage. This integration is
   required before sign-off and is not supplied by the polling process alone.
7. Confirm a real labeled test notification reaches the operator and record delivery
   and recovery evidence. Then enable production-style alerting in staging.

Rollback: stop the separate monitor service; preserve the state volume. No tenant
data/schema rollback is required. Revoke any newly provisioned receiver credentials
if abandoning the integration. Existing API and worker protections remain intact.

The Monitoring & Alerts milestone stays open until hosted deployment, independent
uptime/dead-man monitoring and actual delivery/recovery evidence are complete.
Sprint 7's real-failure retry smoke remains independently pending.

## Suggested initial notification service

Better Stack is a candidate because its [incoming webhook integration](https://betterstack.com/docs/uptime/api/single-incoming-webhook/)
can create/resolve incidents and deliver email, and its [heartbeat monitors](https://betterstack.com/docs/uptime/api/create-a-hearbeat/)
can detect missing pings. No account, subscription, webhook or monitor has been
created. Verify current plan entitlements before subscribing.

The poller sends MONITORING_HEARTBEAT_URL an empty GET only after state persistence.
It withholds the ping if a due alert was not accepted (including disabled delivery).
It logs only accepted/failed/withheld/disabled. Configure an external heartbeat
period of at least 180 seconds with 60 seconds grace for the default polling and
bounded sequential notification sends; review this if thresholds or timeouts change.
A ping confirms monitor execution, not application health. Firing incidents remain
separate. Add an external API liveness check, and explicitly test a missed heartbeat
in a disposable monitor before sign-off.
