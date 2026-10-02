# Confirm a person

In a conversation's People section, choose **Confirm this person**, search existing clients, select the correct client and save. The confirmed name appears alongside the original extracted name. Change or remove the confirmation from the same place. No AI request is used.

This confirms one person mention, not the primary client for the entire conversation. The existing Client link/unlink control still controls that. Transcripts, summaries, task owners, titles and saved drafts are not rewritten. A confirmed name is a snapshot of the chosen client's name at confirmation time; later profile renames do not update it. Review recipient names when drafting. This feature does not merge similarly named clients.

PUT /api/v1/memories/{memory_id}/people/{person_id}/confirmation accepts client_id or null. It checks the nested person's conversation owner and target client owner; foreign and missing IDs return identical 404 details. No provider is called. Migration 0014 adds nullable people.confirmed_name; existing extracted names are preserved.

Release: deploy migration/API before frontend. Check two accounts cannot substitute each other's person, memory or client IDs. Confirm Vail as Vale, reload, change and remove; verify original text and primary conversation link remain unchanged. Verify recovery of the new field in a subsequent backup restore. Application rollback may leave the additive column; migration downgrade deletes confirmation names. Hosted validation remains pending.
