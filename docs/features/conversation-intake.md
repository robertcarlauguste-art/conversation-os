# Conversation Intake

Sprint 1's first end-to-end workflow: a Realtor uploads an audio
recording, ConversationOS stores it and creates a Conversation record,
and the recording appears in the app. No AI processing happens yet —
this is the intake pipeline everything else builds on.

## Upload workflow

```
Realtor picks/drops a file
        ↓
Frontend calls POST /api/v1/conversations (multipart)
        ↓
validators.py checks extension, MIME type, size
        ↓ (fails → 422 with a clear message)
storage.py (LocalStorageBackend) writes the file to disk
        ↓
repository.py persists a Conversation row, status = UPLOADED
        ↓
events.py logs a ConversationUploaded event (no consumers yet)
        ↓
Response: { "success": true, "data": { "id": "...", "status": "UPLOADED" } }
```

Every step of this is logged with a request ID, so `upload_started`,
`upload_completed` (or `upload_failed`), and the final request log
line all share the same `request_id` and can be traced end to end —
see [Observability](../../README.md#observability) in the root README.

## Storage architecture

Uploads go through a `StorageBackend` interface
(`app/conversation/storage.py`), not directly through filesystem
calls — the same pattern as `AIProvider` from Sprint 0. Sprint 1 ships
one implementation, `LocalStorageBackend`, which writes to
`STORAGE_ROOT/conversations/<uuid><extension>` (the original filename
is kept only in the database, not the stored path, to avoid
collisions and path-traversal concerns).

Swapping to Supabase Storage or S3 in a later sprint means adding one
new `StorageBackend` subclass and changing what
`app/conversation/api.py`'s `get_storage_backend` dependency
constructs — no change to `service.py`.

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/conversations` | Upload an audio file (multipart, field name `file`); optional `title` query param. |
| `GET` | `/api/v1/conversations` | List conversations, newest first. |
| `GET` | `/api/v1/conversations/{id}` | Get one conversation's full detail. |
| `DELETE` | `/api/v1/conversations/{id}` | Delete the record and its stored file. |

Accepted formats: `mp3`, `wav`, `m4a`, `aac`. Maximum size: 100 MB.
Every response uses the `{ "success": bool, "data": ... }` envelope
(`app/schemas/envelope.py`) — shared across slices, not
conversation-specific.

## Future pipeline

Per the CTO's Sprint 1 note, every future sprint adds a stage to one
pipeline rather than shipping an isolated feature:

```
Conversation → Intake → Transcription → Knowledge Extraction
→ Relationship Memory → Recommendations → Actions
```

Sprint 1 delivers **Intake**. The `ConversationUploaded` event exists
specifically so Transcription (Sprint 2) can subscribe to it without
Sprint 1's code needing to change.
