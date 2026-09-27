# Pilot limits and expectations

The family-and-friends pilot uses fictional recordings. This is product guidance, not a finalized production privacy policy.

## Current behavior

- Browser recording: three-minute stop; uploads: default 100 MiB application size ceiling. Provider limits may be smaller. These are per-recording limits, not account quotas.
- Client review: at most 50 transcribed conversations, 100 open tasks and 60,000 characters of assembled input. Oversized history is rejected before provider calls. Review generation is requested by the user; saved results can be read without generating again.
- No enforced aggregate account storage allowance or daily AI quota is established by these limits. Do not advertise unlimited storage or AI use.
- Ordinary users are restricted to their own records. Service operators and processing providers are distinct from ordinary users; this is not end-to-end encryption.
- Conversation deletion removes audio first, then the conversation record and dependent results. It does not delete the client or other conversations. Backup/provider removal is not implied by active-app deletion.
- Review source quotes are evidence to inspect, not a guarantee of semantic accuracy. Users must verify summaries and explicitly confirm task completion. No measured accuracy percentage is promised.

## Proposed decisions before wider distribution

Choose aggregate storage and AI quotas from observed per-user costs and pilot usage. Enforce them server-side before describing them as protections; show remaining allowance and a clear limit message. Do not introduce billing without a separate decision.

Confirm active-data retention, backup expiration, provider retention, and the account-data removal process before publishing a production policy. A configured backup lifetime alone does not establish deletion across all systems.

Collect feedback on one complete journey: record, review, correct, find an older conversation, and confirm a finished task. Record missing facts, invented facts, incorrect client links and confusing steps separately.

## Validation sources

AudioRecorder.tsx; core/config.py; client/review.py; conversation/service.py; client/models.py; tenant-isolation security evidence and backup rollout evidence. Hosted configuration may override defaults. This copy-only change adds no quotas, retention job, or deletion endpoint.
