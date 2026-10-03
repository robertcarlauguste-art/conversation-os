# Prepare follow-up

Purpose: help busy professionals turn a conversation into follow-through without replacing their CRM or messaging tools.

On a completed conversation, click **Draft email or text** directly below the summary, select email or text, and explicitly select details safe to share. Nothing is selected by default. Review and edit the generated subject/message, then copy it into the tool you already use. Copying does not send a message or complete any task.

## Initial scope

- Before generation, the optional **Who is this message for?** selector lists confirmed people from this conversation. Nothing is selected automatically. The server validates the person belongs to the selected memory and has a confirmed name; foreign, missing and unconfirmed IDs return the same 404 before AI charging. Only the selected confirmed name and original spelling are added to the provider facts. No other client history/contact details are sent. Confirmation supplies a recipient identity, not a sender identity or permission to transfer commitments. An unspecified recipient requests neutral wording. Existing saved drafts are not changed; recipient choices are generation inputs, not stored recipient metadata or delivery addresses.

- Drafts use only the selected summary and/or tasks from this conversation. No automatic transcript, other conversation, client history, original extraction, or internal-note inclusion.
- Task owner, due wording and status accompany selected tasks. The prompt prohibits invented details and treating a completion flag as proof of delivery.
- Existing user ownership checks apply to both the conversation and nested task IDs. Foreign and missing conversation IDs receive the same 404. Invalid selections do not consume allowance.
- Each provider attempt consumes one shared AI allowance when pilot limits are enabled; provider failures are not refunded. No automatic retries.
- Provider output must validate as bounded JSON; malformed output and provider errors return a generic error without source content or provider diagnostics.
- Save draft stores one email and one text per conversation for its owner. Saving replaces the previous version of that format. Unsaved edits remain page state; browser reload/close uses a best-effort warning, and ordinary same-tab navigation links ask before leaving. Same-page anchors and new-tab clicks remain usable. Back/Forward traversals ask before leaving when the browser exposes a cancelable Navigation API event. Older browsers, non-cancelable traversals (including some repeated Back attempts), and programmatic push/replace navigation are not covered; save before navigating. No synthetic history entries are inserted. A warning remains visible when the editor is collapsed. Clipboard failure offers manual copy.
- GET/PUT drafts endpoints check conversation ownership. Missing and foreign IDs return the same 404. Saves use a parent-row lock and expected version; stale saves return 409 without overwriting. Saving/reopening never consumes AI allowance.
- Migration 0013 adds followup_drafts, cascade-deleted with its conversation. No sending, CRM integration, reply-thread ingestion, or automatic task mutations.

Prompt instructions are not a guarantee of factual accuracy or redaction. The user must choose safe source details and review the draft. Continue using fictional pilot data until the wider privacy/release gates are met.

## Wording review cases

Drafting instructions now avoid invented recipient/sender identities and team language, preserve uncertain completion, and prefer a neutral topical question over narration about the recording. Existing saved drafts are not rewritten.

| Selected facts | Review requirement |
| --- | --- |
| Sending Alex property listings appears completed; no tasks | No assumed greeting to Alex, no claim of sending/receipt, no team voice. A neutral question such as “Any update on the property listings?” is appropriate. |
| Alex owns “Contact lender”; task marked completed | Do not write “I contacted the lender” or treat the completion flag as proof of contact. |
| Sender and recipient are unspecified | Omit named greeting/signature; do not infer either from a person mentioned. |
| A team explicitly promises a proposal Friday | Team wording is permitted only with that support; preserve the owner and Friday commitment. |
| Listings may have been sent, dates conflict | Do not resolve uncertainty by asserting delivery or choosing a date. |

The local source-fidelity tests verify uncertainty and task ownership reach the provider unchanged for both formats. Mocked outputs do not measure model wording quality. Evaluate actual generated messages against these cases in a later authorized pilot run; no extra provider calls are required for the local checks.

## Staging acceptance procedure

Deploy API before frontend after CI passes. With fictional data, test email and text for a consulting conversation, vendor discussion and property showing. Check future versus already-completed statements, ambiguous ownership, conflicting dates/budgets and an internal aside. Omit the summary and verify its unique private detail does not reach the draft. Inspect generated content manually for unsupported claims. Test edits, clipboard fallback, discard confirmation and page-refresh behavior. Verify AI usage increases once and task status remains unchanged.

Repeat with two independent accounts: substitute the other account's conversation and task IDs, compare foreign/missing responses, and verify allowance is unchanged on rejection. Use local automated tests for exhausted allowance and provider errors; do not fabricate a hosted processing failure.

For saved drafts, save each format, refresh and reopen, edit and save again. Open two tabs: save in one, then confirm the stale tab receives a conflict and keeps its edits. Verify both accounts cannot read or overwrite each other's drafts, including direct ID substitution. Check saving/reopening at exhausted AI allowance. Deleting a disposable conversation must delete its drafts. No hosted checks are implied by local test success.

Deploy migration/API before frontend. Back up before migration. Roll back application code while leaving the additive table intact; downgrading 0013 deletes all saved drafts. Include this table in the next backup/restore verification.

Measure draft usefulness, corrections needed and time to reviewed message with actual pilot participants. Historical draft versions and CRM integration remain future work.
