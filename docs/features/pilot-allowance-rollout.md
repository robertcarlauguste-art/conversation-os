# Pilot allowance rollout

Implemented behind `PILOT_LIMITS_ENABLED` (default false). No billing or retention changes.

Limits per authenticated user: 30 active recordings; 250 MiB active audio; five new recordings / 900 decoded seconds per UTC day; 180 decoded seconds per recording; five combined AI client-review and dashboard-briefing requests per day; two explicit processing retries per day. Existing automatic provider/worker retries remain bounded by their own configuration and do not each count as a user request.

Migration 0012 adds a durable owner/day ledger. PostgreSQL transaction advisory locks serialize admissions for each account across API instances. Upload admission and the conversation insert commit together; failure rolls back daily usage. Retry admission commits with the retry transition; queue failure rolls it back. AI admission commits before provider calls, so provider failures and stale-review rejection consume allowance. Validation failures before provider work do not. Reading saved reviews is uncharged. Deletion frees only active slots/storage, not daily usage. Existing over-limit users retain read/edit/delete access.

Duration is measured by bounded ffmpeg decoding, including WebM without duration metadata. Output is capped at 181 seconds of mono 16 kHz PCM, processing at 30 seconds, protocols to local file/pipe and demuxers to supported audio containers. Backend image and CI install ffmpeg. Multipart uploads are spooled by the framework; application reads are bounded to the configured maximum plus one byte. An infrastructure request-size/rate limit remains a separate abuse safeguard.

Authenticated GET /api/v1/usage returns only the current owner's limits, usage, remaining allowance and next UTC reset. The account-isolated frontend cache displays these values and refreshes every 30 seconds, on focus or manually. Backend remains authoritative; the display can briefly lag another tab's activity.

## Activation procedure

1. Verify CI and review the change. Apply migration 0012, then deploy API/worker images containing ffmpeg and frontend code with the flag still false.
2. Enable PILOT_LIMITS_ENABLED=true on the staging API only. Confirm /usage reports enabled, existing data remains readable and the frontend shows remaining allowances.
3. Using synthetic accounts/resources, verify upload duration, foreign-resource 404 behavior, at-limit 429 responses, normal saved reads and deletion freeing storage. No production data or fabricated hosted processing failure is needed.
4. Do not enable on production without its own rollout decision. To disable admission checks, set the flag false and redeploy; keep the ledger and migration intact. No need to drop usage history.

## Boundaries

These limits do not implement a cross-provider dollar ceiling, paid plans, a signup cap or a global decoder concurrency limit. Duplicate requests submitted separately consume separate allowance; automatic HTTP replay idempotency is not implemented. Users should refresh before resubmitting an uncertain upload. Existing records count immediately toward active limits, while daily counters begin with activation and reset at UTC midnight. Daily usage rows contain owner identifiers/counters, not audio or transcript contents.
