# Sprint 2 — Memory & Intelligence

**Status:** Complete. Full pipeline verified end-to-end against real Postgres
and through the real HTTP API (with fake external providers standing in
for the two paid third-party AI calls — see "What couldn't be verified
live" below). Built directly into the authoritative repository (cloned
from a git bundle you provided), on branch
`feature/sprint-2-memory-intelligence`, not committed yet per your
instruction.

## Scope note: this sprint expanded mid-flight, with approval

The original spec's pipeline diagram (`Conversation → LLM → Structured
JSON`) had no transcription step, but no LLM can summarize raw audio —
Anthropic's own published patterns confirm the standard approach is
speech-to-text first, then the transcript goes to an LLM. This was
raised before writing any code; you approved building real
transcription this sprint rather than stubbing it, and approved OpenAI
Whisper as the vendor.

## 1. Architecture Summary

Hybrid architecture unchanged from Sprint 1 (ADR-002/ADR-004): shared
base-class packages (`repositories/`, `services/`, `orchestrator/`,
`providers/`) plus vertical slices per business capability. Two new
slices this sprint: `transcription/` (audio → text) and `memory/`
(text → structured knowledge). One approved amendment to ADR-002 (not
a new ADR): `app/orchestrator/` now holds concrete cross-slice
orchestrators, not only the base class.

**The pipeline** (`ConversationProcessingOrchestrator.run`):

```
conversation.storage_path
    ↓ (StorageBackend.read)
TranscriptionService.transcribe → TranscriptionProvider (Whisper)
    ↓ transcript.text
MemoryService.extract_and_persist → AIProvider (Claude)
    ↓ raw JSON string
json.loads → ExtractionResult (Pydantic validation)
    ↓
validate_extraction (business rules)
    ↓
Memory + Decision[] + ActionItem[] + Person[] persisted in one transaction
```

Events, in order, all logged synchronously (no message broker):
`ConversationUploaded` (Sprint 1) → `ConversationProcessingStarted` →
`TranscriptionCompleted`/`TranscriptionFailed` → `MemoryCreated` →
`ActionItemsExtracted` → `ConversationProcessed`.

## 2. Data Model

**`transcripts`** — one row per conversation (unique constraint on
`conversation_id`): `id`, `conversation_id` (FK, cascade delete),
`text`, `language`, `status`, `error_message`, timestamps.

**`memories`** — one row per conversation: `id`, `conversation_id`
(FK, cascade delete, unique), `title`, `summary`, `memory_type`,
`topics` (string array), `confidence`, `source`, timestamps.

**`decisions`** / **`action_items`** / **`people`** — child tables,
each with `memory_id` FK (cascade delete), so future sprints can
query/dedupe them independently.

**Design note on topics:** modeled as a string array column on
`Memory` rather than a fifth table — decisions/action items/people
have clear independent identity; topics are just labels with no
lifecycle of their own yet.

## 3. AI Pipeline

Two external AI vendors, two abstractions: `TranscriptionProvider`
(new, sibling to `AIProvider`) with `OpenAIWhisperProvider` as the
concrete implementation (raw `httpx` call, not the full `openai` SDK,
for one endpoint); `AIProvider` (Sprint 0 interface) with
`ClaudeProvider` as its first concrete implementation. Schema
validation before persistence: `json.loads` → `ExtractionResult`
(Pydantic) → `validate_extraction` (business rules).

## 4. Events

Implemented exactly as specced, still synchronous/in-process/logged —
no message broker, no background workers. `conversation/events.py`
gained `ConversationProcessingStarted` and `ConversationProcessed`;
`transcription/events.py` and `memory/events.py` are new.

## 5. API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/memories` | List all memories, newest first |
| `GET` | `/api/v1/memories/{id}` | Get one memory by its own id |
| `GET` | `/api/v1/memories/by-conversation/{conversation_id}` | Get the memory for a conversation |
| `GET` | `/api/v1/transcriptions/by-conversation/{conversation_id}` | Get the transcript for a conversation |

Both read-only. `POST /api/v1/conversations` now triggers the full
pipeline as a side effect; response shape unchanged, but `status` now
reflects the pipeline's outcome.

## 6. Frontend

Replaced Sprint 1's three placeholder cards (Transcript/Knowledge/Tasks)
on the Conversation Detail page with `MemoryPanel`: Summary (with topic
pills and confidence/source footer), Decisions/Action Items/People as
a 3-column grid, collapsible Transcript (kept even though the spec's
frontend section didn't explicitly list it — felt wrong to compute a
transcript and hide it; noted as an assumption). Loading state (waveform
pulse + polling while `PROCESSING`/`UPLOADED`), empty state, and a
distinct failed-state message. Same design language as Sprint 1.

## 7. Testing

**40/40 backend tests pass**, run against this repository's real
Postgres. New this sprint: `transcription/tests/` (service + API),
`memory/tests/` (validators, repository, service integration, API),
and `conversation/tests/test_api.py` rewritten — one test patches in
fake providers via `monkeypatch` (patching where used, in
`app.orchestrator.dependencies`) to exercise the real
orchestrator/services/DB end-to-end; a second deliberately doesn't
patch anything, confirming the real "no API keys configured" path
degrades to `status: FAILED` without a 500.

`ruff`, `black --check`, `mypy` all clean. Frontend `eslint`,
`tsc --noEmit`, and a real `next build` all pass.

## What was verified live vs. what wasn't

**Verified for real, against this actual repository** (cloned from
your bundle, not a separate sandbox copy): migrations `0001`→`0003`
ran against real Postgres 16 + pgvector; the full pipeline end-to-end
through the real HTTP API (`ASGITransport`) using fake providers —
upload → transcribe → extract → persist → `status: COMPLETED`; all 40
automated tests; real lint/type checks; real frontend build.

**Not verified live** — flagged, not hidden: the actual outbound calls
to `api.openai.com` (Whisper) and `api.anthropic.com` (Claude) with
real credentials. No API key configured for either in this
environment, and no network path to `api.openai.com` at all from this
sandbox. **Please smoke-test both against real keys and a real audio
file before relying on this in production.**

## Technical Debt

**TD-001 (from Sprint 1, now partially addressed):** trigger condition
arrived this sprint — `transcription/` needs to read stored audio.
`StorageBackend` gained a `read()` method; `transcription/` imports
`app.conversation.storage` directly (cross-slice import, tracked not
solved). Recommend moving to shared infra in Sprint 3.

**TD-002 (from Sprint 1, unchanged):** legacy `app/events/` stub still
unaddressed.

**TD-003 (new this sprint):** Upload triggers the full pipeline
*synchronously*, inside the request/response cycle. Deliberate
simplicity tradeoff (no new queue infrastructure, deterministic
tests), not an oversight — revisit once real-vendor latency or retry
needs make it user-visible.

## Assumptions Made This Sprint

1. Transcription output is persisted (not just piped in-memory) —
   worth it since a transcript is independently useful later.
2. The transcript is displayed on the Conversation Detail page even
   though the spec's frontend section didn't list it.
3. `action_items.owner` and `people.role` exist as columns but are
   always `null` this sprint — the extraction prompt doesn't ask for
   them yet.
4. Only one `Memory` per `Conversation` this sprint (unique
   constraint) — re-processing isn't supported yet.

## Recommendations for Sprint 3

1. Smoke-test `ClaudeProvider` and `OpenAIWhisperProvider` against real
   credentials and a real audio file before this reaches a production
   user.
2. Move `storage.py` to shared infrastructure (TD-001).
3. Decide on TD-003 (synchronous vs. background processing).
4. Resolve TD-002 (delete or repurpose `app/events/`).
5. If Sprint 3 needs to *react* to `ConversationProcessed`/
   `MemoryCreated` (e.g. sending a follow-up email), that's the point
   where "orchestrator calls event functions directly" stops being
   adequate and a real pub/sub mechanism deserves its own ADR.
