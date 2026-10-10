# Transcript corrections

Original speech-recognition text remains immutable. A completed conversation can have one saved correction with an optimistic version number. Saving clears its previous generated preview, costs no AI usage, and changes no original notes, tasks, completion statuses, person confirmations, client links or saved drafts.

A separate user-requested notes preview consumes the shared AI allowance when enabled, including provider failures. Output is validated and persisted only if the saved correction version still matches. Preview tasks are suggestions, not new task records. Users review the preview and manually edit existing tasks; automatic application is deliberately absent to avoid duplication or loss of completed/edited work. Existing briefing, review and drafting flows still use their original data, not the preview.

Migration 0016 adds the correction table. Deleting a conversation cascades to its correction and preview. Deploy the backend migration before frontend. Obtain a verified backup before staging migration. Do not downgrade a populated table without preserving its corrections.

Validation includes original retention, tenant ownership, conflicting saves, stale generated results, deletion cascade, provider error redaction and UI save failure retention. Native-speaker review and hosted fictional checks remain release gates.
