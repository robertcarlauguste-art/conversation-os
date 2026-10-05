# Undo a client merge

Clients now has a Recent merges & undo panel listing the owner's latest 20 merges, the original names, date, and undo status. Undo requires a separate confirmation. Help explains the flow and limitations.

New merges save original client details, source creation date, link assignments and manual-assignment flags, plus a fingerprint of the resulting profile and linked content. Undo locks the audit, retained client and linked rows. It rejects a missing/recreated client, older snapshot, repeated undo, or changed post-merge state. Changes to recordings, links, profiles, notes, tasks, people, facts, follow-up events and drafts block undo. New child references are serialized through PostgreSQL parent row locks. Only an unchanged merge restores the original source ID/details, saved reviews, links and manual-assignment flags in one transaction. The audit remains and records the undo time. No AI request is used.

No database migration is required: versioned metadata uses the existing audit JSON column. Earlier merges lack a trustworthy post-merge fingerprint and manual-assignment snapshot, so they require manual recovery review. An older merge may remain blocked after a later merge is undone because timestamps have changed; safe manual review is preferable to guessing. This initial interface is English and lists only the latest 20 merges.

Validation: PostgreSQL merge/undo round trip, preservation, changed-data rejection, foreign/missing IDs, owner-scoped history, rollback on commit failure, duplicate/concurrent undo, and new saved draft protection. Frontend tests cover confirmation/cancel, success, conflicts and legacy snapshots. Authentication inventory includes both new routes.

Before deployment: all CI checks must pass. Hosted verification should use disposable fictional records, verify successful undo and rejection after edits, confirm two-account isolation, and verify backup retention of undo audit state. Existing client records must not be merged or restored as part of rollout tests.
