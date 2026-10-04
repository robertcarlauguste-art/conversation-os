# Confirmed client merge — local review checkpoint

Implemented: history/search first on client profile; compare two records on current list page; explicit preview, retained contact details, moved counts, typed retained-name confirmation, transactional merge.

New migration 0015 adds owner-scoped merge audit snapshots. Source identity, both saved client reviews and original record links are archived. Retained contact fields win; conversation/person/fact/follow-up links move without rewriting transcript/task/confirmed-name content. Saved current review is cleared. Source client is removed from the list. No end-user undo yet. Similar names never trigger automatic merging.

Validation: isolated PostgreSQL full migration upgrade through 0015 passed. Backend client suite 40 passed, 10 opt-in tests skipped; includes 7 new merge tests for ownership/HTTP denial, stale preview, same-record rejection, transactional rollback and relationship/provenance preservation. Backend changed files Ruff/Black checked and merge module mypy passed. Frontend production build passed; full suite 88 passed, then new confirmation test passed separately; lint and typecheck passed with that test included.

Not deployed; no real client merge performed. Deployment needs fresh verified backup, migration 0015, API and frontend release, and fictional two-account smoke checks. Snapshot backup/retention should include the new audit table. No migration downgrade once real audit history exists without exporting/preserving it. Comparison is currently English and current-result-page only. No UI undo; recovery needs operator audit review. Concurrent merge locking exists but a dedicated concurrency stress test is not yet recorded.
