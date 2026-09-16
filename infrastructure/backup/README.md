# Staging backup job

Staging activated September 16, 2026 after an authenticated isolated restore.
First backup: 2026-09-16T05:43:18Z. All ten public tables matched the live database
by counts and full-row fingerprints. Migration 0008 and all constraints verified;
both synthetic tenants retained distinct owners and scoped foreign-ID queries
returned no rows. Restore and comparison took 18.804 seconds on the small dataset.
This is database recovery evidence, not a fresh API authorization test or audio backup.

One-shot PostgreSQL 18 export, AES-256-GCM encryption, upload, full download/hash
verification, immutable manifest, then success heartbeat. Errors exit nonzero and
do not expose provider response details. No app imports, AI calls, restore command,
deletion, retention cleanup or public endpoint. Export capped at 256 MiB and four
minutes for this proof of concept. Failed uploads can leave orphaned objects.

Service: `database-backup`, root `/infrastructure/backup`, daily at 06:00
UTC, one replica, restart NEVER, no public networking and no attached volume.
Use a dedicated missed-run heartbeat (24-hour period, 1-hour grace), verified email
recipient. Existing acceptance-test heartbeat 493760 was repurposed, retaining its
previously verified email delivery path. It is active with a one-day period and
one-hour grace; daily scheduled execution itself still needs observation.

R2 bucket: `conversation-os-staging-backups`, private, no public domain.
The credential is scoped ONLY to this bucket with object read/write access.
It expires October 15, 2026 and must be renewed before then.
Do not reuse the application's recording credential. Retention deletion is deferred
until restore verification and explicit retention selection. Storage/compute usage
still applies; this avoids the Railway Pro requirement, not all usage charges.

Required secret environment variables:

- BACKUP_DATABASE_URL: private staging PostgreSQL URL (read-only backup login preferred).
- BACKUP_ENDPOINT_URL: existing Cloudflare account's HTTPS R2 S3 endpoint.
- BACKUP_BUCKET: the dedicated backup bucket.
- BACKUP_ACCESS_KEY_ID and BACKUP_SECRET_ACCESS_KEY: bucket-scoped credential.
- BACKUP_ENCRYPTION_KEY: base64-encoded random 32-byte AES key.
- BACKUP_KEY_ID: non-secret key version label, e.g. staging-v1.
- BACKUP_HEARTBEAT_URL: dedicated private success heartbeat URL.

Store the recovery key independently in the owner's password manager before the
first real export. Losing the key loses the backups. Never paste keys into chat or
commit them. Provisioning credentials requires approval of the exact access grant.

Acceptance procedure: run once, verify encrypted object plus manifest, restore
to an isolated database with required extensions, verify actual application schema
and tenant checks, and verify missed-backup email alerts. Database exports do not
cover recordings, global roles, Redis or identity/configuration dependencies.

Archive format: ASCII COSBACKUP1, 12-byte nonce, ciphertext, 16-byte GCM tag.
Header is authenticated as associated data. A recovery tool must authenticate the
entire archive before feeding plaintext to pg_restore. This job has no restore
entrypoint; live restoration is intentionally a separate reviewed procedure.

Working branch preserves configuration-validation, tenant-security and monitoring
changes from 647b8b8. No original-checkout files were edited.
