# Operator monitoring and alerts

Status: implementation ready for review; not deployed or signed off. Better Stack
Free is selected; incoming webhooks require an upgrade, so use the operational
health heartbeat mode below. Delivery is not yet connected to Railway.
Configuration validation and
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
| MONITORING_ALERT_HEARTBEAT_URL | Alternative to webhook: secret HTTPS heartbeat base URL, no query; must differ from process heartbeat |
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

### Free heartbeat mode (selected)

Set MONITORING_ALERT_HEARTBEAT_URL and leave MONITORING_WEBHOOK_URL unset.
Configure one heartbeat named `ConversationOS Staging Operational Health` and a
separate `ConversationOS Staging Monitor` process heartbeat. Use a 3-minute period
and 1-minute grace for both. Do not reuse either URL for the other purpose.

Any unhealthy signal makes overall health unhealthy; recovery requires all signals
to be known and healthy. After the consecutive-observation threshold, the poller
sends an empty GET to the base URL for health or to its `/fail` path for failure.
It refreshes the confirmed state each poll, including after restart. An announced
failure stays failed until recovery is confirmed. Unknown/unconfirmed observations
without an announced failure receive no health ping; once activated, the external
deadline detects prolonged uncertainty. Empty signal sets never count as healthy.

This produces one aggregate incident per environment, not a separate incident for
each code. Multiple simultaneous faults and changing faults remain one incident;
consult the private `monitor_poll` signals to identify them. The debounce threshold
applies to overall health. The process heartbeat confirms execution and is not a
substitute for this health heartbeat. A new heartbeat remains pending until its
first ping, so verify activation explicitly during deployment.

No customer content, counts or diagnostic payload is transmitted. Failed delivery
retries on the next eligible poll; redirects are rejected. The hosted acceptance
test must prove repeated `/fail` pings do not create duplicate incidents, that
recovery closes the incident, and that missing pings alert the operator.

### Optional JSON webhook mode

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
4. Begin without either alert delivery URL and run `--once` for a read-only staging
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

## Notification service checkpoint (2026-09-15)

Better Stack Free is configured for email to the primary responder. No paid
subscription was purchased. The custom incoming-webhook feature is paid and is
not used. [Heartbeat failure reporting](https://betterstack.com/docs/uptime/cron-and-heartbeat-monitor/)
provides the free delivery mechanism above.

- API monitor: `4931590`, ConversationOS Staging API; `/health`, 3-minute checks,
  1-minute confirmation, 3-minute recovery, 10-second timeout, redirects disabled.
- Process heartbeat: `493621`, ConversationOS Staging Monitor; pending until wired.
- Health heartbeat: `493748`, ConversationOS Staging Operational Health; pending.
- Both heartbeats: 3-minute period, 1-minute grace, email enabled, no team escalation.
- Better Stack reported sending a process-heartbeat test alert; inbox receipt is
  not yet confirmed. No real failure/recovery or missed-heartbeat proof yet.

Store the secret heartbeat URLs only in the monitoring service configuration.
These two heartbeats per environment leave capacity for staging and initial
production within the currently advertised ten free heartbeats.

The poller sends MONITORING_HEARTBEAT_URL an empty GET only after state persistence.
It withholds the ping if a due alert was not accepted (including disabled delivery).
It logs only accepted/failed/withheld/disabled. Configure an external heartbeat
period of at least 180 seconds with 60 seconds grace for the default polling and
bounded sequential notification sends; review this if thresholds or timeouts change.
A ping confirms monitor execution, not application health. Firing incidents remain
separate. Add an external API liveness check, and explicitly test a missed heartbeat
in a disposable monitor before sign-off.
