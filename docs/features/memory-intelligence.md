# Memory & Intelligence

Sprint 2's workflow: turn an uploaded conversation into structured,
queryable knowledge — a summary, decisions made, action items,
people involved, and topics discussed — with no manual step required.

## Pipeline

```
Conversation uploaded (Sprint 1)
        ↓
ConversationProcessingOrchestrator.run(conversation_id)
        ↓
status → PROCESSING, ConversationProcessingStarted logged
        ↓
TranscriptionService.transcribe()
   reads audio via StorageBackend.read()
   calls TranscriptionProvider (OpenAIWhisperProvider)
   persists a Transcript row
        ↓ TranscriptionCompleted (or Failed)
MemoryService.extract_and_persist()
   calls AIProvider (ClaudeProvider) with the transcript text
   parses the JSON response, validates it (ExtractionResult + validators.py)
   persists Memory + Decision[] + ActionItem[] + Person[] in one transaction
        ↓ MemoryCreated, ActionItemsExtracted
status → COMPLETED, ConversationProcessed logged
   (or → FAILED, logged with a traceback, on any exception above)
```

Runs synchronously inside the upload request (see `Sprint2.md`'s
TD-003) — by the time the upload HTTP response returns, processing
has already succeeded or failed.

## Why transcription is in this sprint at all

The original plan treated Transcription and Knowledge Extraction as
separate sprints. But no LLM API — including Anthropic's — transcribes
raw audio; the standard pattern (confirmed against Anthropic's own
published examples before writing any code) is speech-to-text first,
then the transcript goes to an LLM. Building only the extraction half
this sprint would have had nothing real to extract from. This was
raised as a question before any code was written; the scope expansion
to include real transcription (OpenAI Whisper) was explicitly
approved rather than assumed.

## Schema validation

The LLM is prompted to return only a JSON object in a fixed shape
(`memory/service.py`'s `EXTRACTION_SYSTEM_PROMPT`). Two validation
layers run before anything touches the database:

1. **`ExtractionResult`** (Pydantic) — type and range checks: summary
   non-empty, confidence between 0 and 1, all list fields present
   (defaulting to empty rather than missing).
2. **`validate_extraction`** (`memory/validators.py`) — business rules
   Pydantic can't express: no blank entries in any list, a size cap
   on every list (50 items) and the summary (5000 characters) so a
   malformed or runaway LLM response can't create thousands of rows.

Either layer raising means nothing is persisted — the conversation's
status becomes `FAILED` instead.

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/memories/by-conversation/{conversation_id}` | The memory for one conversation |
| `GET` | `/api/v1/memories/{id}` | One memory by its own id |
| `GET` | `/api/v1/memories` | All memories, newest first |
| `GET` | `/api/v1/transcriptions/by-conversation/{conversation_id}` | The transcript for one conversation |

All read-only — nothing in this slice's API creates data; the
orchestrator does that as a side effect of upload.

## What's verified vs. what needs a real smoke test

The pipeline logic, database persistence, event sequencing, and
failure handling are all verified against a real Postgres database and
the real HTTP API (see `Sprint2.md`'s verification section) — using
fake AI/transcription providers so no real API keys or network calls
were needed. The actual outbound calls to `api.anthropic.com` and
`api.openai.com` were not exercised live in the environment this was
built in (no configured API key for either, and no network path to
`api.openai.com` at all). **Smoke-test both real providers against a
real audio file before relying on this in production.**

## Future pipeline

```
Conversation → Intake → Transcription → Knowledge Extraction
→ Relationship Memory → Recommendations → Actions
```

Sprint 2 delivers Transcription and Knowledge Extraction together.
`ConversationProcessed` and `MemoryCreated` exist so **Relationship
Memory** (linking knowledge across multiple conversations with the
same client, rather than one conversation at a time) can subscribe to
them in a future sprint without changing this sprint's code.
