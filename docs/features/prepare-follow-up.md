# Prepare follow-up

Purpose: help busy professionals turn a conversation into follow-through without replacing their CRM or messaging tools.

On a completed conversation, click **Draft email or text** directly below the summary, select email or text, and explicitly select details safe to share. Nothing is selected by default. Review and edit the generated subject/message, then copy it into the tool you already use. Copying does not send a message or complete any task.

## Initial scope

- Drafts use only the selected summary and/or tasks from this conversation. No automatic transcript, other conversation, client history, original extraction, or internal-note inclusion.
- Task owner, due wording and status accompany selected tasks. The prompt prohibits invented details and treating a completion flag as proof of delivery.
- Existing user ownership checks apply to both the conversation and nested task IDs. Foreign and missing conversation IDs receive the same 404. Invalid selections do not consume allowance.
- Each provider attempt consumes one shared AI allowance when pilot limits are enabled; provider failures are not refunded. No automatic retries.
- Provider output must validate as bounded JSON; malformed output and provider errors return a generic error without source content or provider diagnostics.
- Drafts are temporary page state, not durable history. Refreshing or leaving the page loses them. Discard requires confirmation. Clipboard failure offers manual copy.
- No sending, CRM integration, reply-thread ingestion, new migration, or automatic task mutations.

Prompt instructions are not a guarantee of factual accuracy or redaction. The user must choose safe source details and review the draft. Continue using fictional pilot data until the wider privacy/release gates are met.

## Staging acceptance procedure

Deploy API before frontend after CI passes. With fictional data, test email and text for a consulting conversation, vendor discussion and property showing. Check future versus already-completed statements, ambiguous ownership, conflicting dates/budgets and an internal aside. Omit the summary and verify its unique private detail does not reach the draft. Inspect generated content manually for unsupported claims. Test edits, clipboard fallback, discard confirmation and page-refresh behavior. Verify AI usage increases once and task status remains unchanged.

Repeat with two independent accounts: substitute the other account's conversation and task IDs, compare foreign/missing responses, and verify allowance is unchanged on rejection. Use local automated tests for exhausted allowance and provider errors; do not fabricate a hosted processing failure.

Measure draft usefulness, corrections needed and time to reviewed message with actual pilot participants. Durable draft history and one CRM integration are follow-on decisions, not shipped capabilities of this version.
