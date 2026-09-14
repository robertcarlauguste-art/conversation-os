# Proposed staging security verification

Status: procedure prepared; NOT deployed or executed against hosted accounts.
Configuration validation remains in the candidate's ancestry at `e818ad7`.
Sprint 7's genuine-failure retry smoke remains pending.

## Release preparation

1. Review the authorization inventory in `docs/features/tenant-isolation-security.md`
   and this milestone's diff relative to `e818ad7`. Review/merge PR #13 through the
   normal process first, then integrate this branch and run CI on the resulting
   commit. Do not deploy current `main` without verifying configuration validation
   is present. A squash merge changes ancestry: verify the actual configuration
   files and tests rather than relying only on the old commit ID.
2. Use a clean isolated release checkout. Do not copy or reset the original working
   tree; its uncommitted retry tests and processing notes are unrelated work.
3. Snapshot current staging API, worker and frontend deployment IDs, source commit,
   and configuration names (never values). Existing checkpoint rollback references:
   API `4788e2c9-40d4-459e-92c5-81096d1dd251`, worker
   `4f41decc-2528-48ac-b469-520c9d95703a`, frontend
   `ae66b498-1228-48ad-8cda-7eaa8fb49f45`. Verify these are still the intended
   rollback releases before using them.
4. Run backend/frontend CI and builds on the exact candidate. No schema migration
   is introduced by this milestone. Preflight the existing hosted configuration
   validator, authentication, database, Redis and private R2 storage settings.
5. Deploy API, worker, then frontend to **ConversationOS Staging / staging** only,
   recording each deployment ID. Verify `/health`, `/ready`, `/version`, signed-in
   dashboard, and a fresh upload. Confirm the built frontend contains the account
   cache fix and all services correspond to the reviewed candidate.

## Two-account adversarial smoke

Use two independent staging Clerk users in separate browser profiles, A and B.
Use synthetic recordings with distinct client names, transcript phrases, summary
topics, decisions and action items. Upload one as each user and allow normal
processing to complete. Record resource IDs and expected ownership in a private
test worksheet. Do not record tokens, object credentials, recording contents, or
signed URLs in shared logs. Each user must successfully access their own resources
before testing denials, so a broken endpoint cannot masquerade as isolation.

For every probe below, run A→B and B→A. Call the API directly with the actor's
fresh token, bypassing the UI. Compare a known foreign UUID with a fresh nonexistent
UUID using the same valid request. Expected: 404 with the same response shape and
message after normalizing the caller-supplied UUID. No names, contents, processing
state, object keys or other existence signals should appear. Check the owner's
view after denied mutations to verify nothing changed.

| Probe | Request and expected result |
| --- | --- |
| Conversation detail / processing metadata | GET `/api/v1/conversations/{foreign}` → 404. |
| Delete | DELETE the same resource → 404; owner's recording/results remain. |
| Retry | POST `/api/v1/conversations/{foreign}/retry` → 404 even when the foreign conversation is completed; must not return the owner's 409 status conflict or enqueue a job. |
| Transcript | GET `/api/v1/transcriptions/by-conversation/{foreign}` → 404. |
| Summary, decisions, people, actions | GET `/api/v1/memories/by-conversation/{foreign}` and GET `/api/v1/memories/{foreign_memory}` → 404. |
| Action mutations | POST `/api/v1/memories/action-items/{foreign_action}/complete` and `/reopen` → 404; owner sees unchanged status. |
| Client and nested list | GET `/api/v1/clients/{foreign}` and `/{foreign}/conversations` → 404. |
| Link and unlink | POST and DELETE `/api/v1/clients/{client}/conversations/{conversation}` with own/foreign, foreign/own, and foreign/foreign pairs → 404. Positive own/own link/unlink works. |
| Follow-up mutations | POST `/api/v1/dashboard/recommendations/{foreign_client}/actions` with valid complete, record_contact and snooze bodies → 404. Own requests work. |
| Lists / filters | Conversation, client and memory lists exclude foreign IDs/content. Search foreign title/filename/name/email/phone, wildcard terms, role/status filters and pagination; no foreign records or counts. |
| Dashboard / AI briefing | GET `/api/v1/dashboard`, POST `/api/v1/dashboard/briefing` include only actor records and recommendations, including recent/completed actions and linked-client names. |
| Operations | GET `/api/v1/operations` shows actor counts only, `queue_depth: null`, `worker_available: null`, and no infrastructure alerts. Create a normal additional upload in B and verify A's counts/alerts do not change. Ordinary users and organization-admin claims receive no global workload metadata. |
| Upload ownership | POST multipart `/api/v1/conversations` with an extra foreign owner/client/storage-path query parameter cannot redirect ownership or select an existing object; the new resource belongs to actor only. Delete this synthetic upload as its owner. |
| Authentication | Replay all business requests without token, with invalid/expired token, and with forged identity/role headers → 401. `/api/v1/auth/me` identifies only the actual verified actor. |
| Browser account switch | In a single tab, view A's dashboard/results, switch to B (and sign out), including while a request is slow. No A data may flash or remain cached in B's session. Repeat B→A and a new session for the same user. |

The product currently isolates by user, not organization. If organization membership
is available for the test accounts, also put both users in the same test organization:
membership or an org-admin label must not grant access to each other's records.
There is no application administrator endpoint/role in this release.

## Storage and job checks

- Verify R2 bucket public access and any custom/public domain are disabled. Using
  operator-known synthetic object locations, verify unsigned GET/list requests and
  requests carrying only a Clerk application token return no object bytes. Compare
  existing and nonexistent objects for distinguishable existence information. This
  is a hosted infrastructure test; mocked S3 unit tests cannot establish it.
- Confirm API JSON and browser network responses never expose `storage_path`,
  object keys, presigned URLs or credentials. There are no download, presign,
  upload-finalize, client-delete or raw queue/job API routes to exercise. Confirm
  attempted raw storage/job paths return no resource data (404/405 for unsupported
  routes/methods), and there is no separately configured public storage proxy.
- Review the worker logs for these synthetic IDs: owner context stays attached to
  the job; no cross-account writes occur. Do not directly alter staging Redis job
  payloads. Mismatched worker payloads are tested in the local automated suite.
- If a **genuine** failed hosted conversation exists, run the existing owner's
  retry smoke and verify the other account receives 404. If none exists, record
  that positive hosted retry check as pending. Do not break a provider, corrupt
  configuration, or manufacture a hosted failure to satisfy it.

## Sign-off and rollback

Save candidate commit, deployment IDs, timestamp, account aliases, test-resource
aliases, method/path, status, normalized response comparison, and owner-side
postcondition for each probe. Do not mark the security milestone complete until
both directions, real Clerk verification, account switching and private storage
checks pass. List any untested surface explicitly.

If any unauthorized data is visible, stop the smoke and keep launch blocked.
Revert the staging services to the verified rollback releases if needed; note that
those older releases retain the defects identified here, so rollback is operational
recovery, not a security sign-off. Preserve sanitized evidence and fix the candidate
before repeating affected checks. Remove only the synthetic conversations using
their owning accounts; there is no client-delete API, so any leftover synthetic
clients need the project's separately approved cleanup process.
