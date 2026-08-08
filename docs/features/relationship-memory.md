# Relationship Memory

Sprint 3's workflow: recognize the same client across separate
conversations and maintain one durable, continuously-updated profile
of what's known about them, rather than each conversation's memory
staying isolated (Sprint 2's state of the world).

## Read this first: current real-world effectiveness

**Automatic matching is implemented correctly but is currently inert
against real conversations.** Sprint 2's extraction never populates
`Person.role`, and role is the corroborating attribute FD-003
requires alongside name — no role means no automatic match is even
attempted, by design. In practice today, every reconciliation creates
a new `Client`. This isn't a bug in Sprint 3; it's the correct,
conservative behavior of "never merge on name alone" given what
Sprint 2 actually extracts. See `Sprint3.md` (TD-006) and
[ADR-005](../adr/005-client-matching-strategy.md) for the full
account, and the recommendation to extend extraction in Sprint 4.

## Pipeline

```
Memory extracted (Sprint 2's MemoryCreated)
        ↓
ConversationProcessingOrchestrator._reconcile_people_to_clients()
        ↓
for each Person in memory.people:
    ClientService.find_or_create(name, role, conversation_id)
        — exact name + exact role match → existing Client (ClientMatched)
        — no match, or no role present → new Client (ClientCreated)
    MemoryService.link_person_to_client(person.id, client.id)
        ↓
for each unique Client matched/created this memory:
    ClientService.record_facts(client_id, memory.topics, ...)
        — every fact carries source_conversation_id, source_memory_id,
          and created_at (FD-005) — not optional
        ↓ ClientProfileUpdated
primary client (first non-agent role, else first person) →
    conversation.client_id
```

Wrapped in its own `try/except` inside the orchestrator — a matching
failure doesn't undo an otherwise-successful transcription and
extraction; the conversation still completes, and the failure is
logged with the conversation and memory IDs.

## Manual correction (US-105)

Automatic matching being sometimes wrong (or, currently, always
absent) is an expected, designed-for outcome, not a bug to route
around. `POST`/`DELETE
/api/v1/clients/{client_id}/conversations/{conversation_id}` let a
human link or unlink a conversation directly. The Conversation Detail
page's "Client" field surfaces this: a linked client's name with an
Unlink action, or "Unmatched" with a minimal link-by-ID input (no
search/autocomplete yet — TD-004).

## Why facts come from `topics`, not a dedicated extraction field

The product vision describes facts like "prefers 3-bedroom homes" —
richer than Sprint 2's `memory.topics` (short labels like
"financing", "timeline"). Building dedicated fact extraction would
mean modifying Sprint 2's tested LLM prompt, which was out of this
sprint's approved scope. `client_facts` reuses `topics` verbatim for
now — documented as TD-005, not silently passed off as the richer
thing the vision describes.

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/clients` | List clients |
| `GET` | `/api/v1/clients/{id}` | Client profile with facts |
| `GET` | `/api/v1/clients/{id}/conversations` | Linked conversations (US-104) |
| `POST` / `DELETE` | `/api/v1/clients/{client_id}/conversations/{conversation_id}` | Manual link/unlink (US-105) |

## What's verified vs. what needs a real smoke test

Verified for real: the full reconciliation pipeline through the real
HTTP API (fake AI/transcription providers, real Postgres) — confirmed
live that two people with no role each become separate new clients
(not a false match), facts persist with correct provenance, a primary
client gets linked, and manual unlink correctly clears `client_id`.
Migration `0004` verified both `upgrade` and `downgrade`.

Not verified: real-vendor extraction quality (carried over from
Sprint 2 — `ClaudeProvider`/`OpenAIWhisperProvider` still need a
smoke test against real credentials), and — new this sprint —
matching quality against real extracted names/roles, since role
doesn't exist in real extraction output yet to test against.

## Future pipeline

```
Conversation → Intake → Transcription → Knowledge Extraction
→ Relationship Memory → Recommendations → Actions
```

Sprint 3 delivers Relationship Memory's plumbing; making automatic
matching actually fire against real conversations is Sprint 4's
first job. **Recommendations** (surfacing what to do next based on a
client's remembered facts) and **Actions** (drafting follow-ups) are
future pipeline stages this sprint doesn't touch.
