"""Conflict-checked reversal of a merge; never overwrite subsequent work."""

import hashlib
import json
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select, text, update

from app.client.models import Client, ClientFact, ClientMergeAudit
from app.conversation.models import Conversation
from app.dashboard.models import ClientFollowupAction
from app.memory.models import ActionItem, Decision, Memory, Person
from app.transcription.models import Transcript

LINKED = (Conversation, Person, ClientFact, ClientFollowupAction)


async def merged_state(session, target_id):
    """Lock and fingerprint the retained profile and its entire linked content.

    Parent locks also prevent new FK references during the reversal. Raw column
    reads avoid stale ORM identities after bulk updates. No content goes to UI.
    """
    state = {}

    async def rows(model, condition):
        table = model.__table__
        found = (
            (
                await session.execute(
                    select(table).where(condition).order_by(table.c.id).with_for_update()
                )
            )
            .mappings()
            .all()
        )
        state[table.name] = [dict(row) for row in found]
        return found

    await rows(Client, Client.id == target_id)
    conversations = await rows(Conversation, Conversation.client_id == target_id)
    for model in LINKED[1:]:
        await rows(model, model.client_id == target_id)
    conversation_ids = [row["id"] for row in conversations]
    memories = await rows(Memory, Memory.conversation_id.in_(conversation_ids))
    memory_ids = [row["id"] for row in memories]
    for model in (ActionItem, Decision, Person):
        found = (
            (
                await session.execute(
                    select(model.__table__)
                    .where(model.memory_id.in_(memory_ids))
                    .order_by(model.id)
                    .with_for_update()
                )
            )
            .mappings()
            .all()
        )
        state["memory_" + model.__tablename__] = [dict(row) for row in found]
    await rows(Transcript, Transcript.conversation_id.in_(conversation_ids))
    drafts = await session.execute(
        text(
            "SELECT to_jsonb(d) FROM followup_drafts d "
            "WHERE conversation_id = ANY(CAST(:ids AS uuid[])) "
            "ORDER BY conversation_id, channel FOR UPDATE"
        ),
        {"ids": [str(value) for value in conversation_ids]},
    )
    state["drafts"] = list(drafts.scalars())
    return hashlib.sha256(json.dumps(state, sort_keys=True, default=str).encode()).hexdigest()


async def undo_merge(session, owner_id, audit_id):
    try:
        audit = await session.scalar(
            select(ClientMergeAudit)
            .where(ClientMergeAudit.id == audit_id, ClientMergeAudit.owner_id == owner_id)
            .with_for_update()
        )
        if audit is None:
            raise HTTPException(404, "Merge not found.")
        snapshot = audit.snapshot
        if snapshot.get("undone_at"):
            raise HTTPException(409, "This merge has already been undone.")
        if snapshot.get("undo_version") != 1:
            raise HTTPException(409, "This older merge needs manual recovery review.")
        target = await session.scalar(
            select(Client.id)
            .where(Client.id == audit.target_id, Client.owner_id == owner_id)
            .with_for_update()
        )
        if target is None or await session.scalar(
            select(Client.id).where(Client.id == audit.source_id)
        ):
            raise HTTPException(
                409, "Client records changed. Undo cannot safely restore this merge."
            )
        if await merged_state(session, audit.target_id) != snapshot["after_digest"]:
            raise HTTPException(
                409,
                "These records changed after the merge. Undo was stopped to protect newer work. "
                "Ask for help reviewing the changes.",
            )
        source = Client(
            id=audit.source_id,
            owner_id=owner_id,
            **snapshot["source"],
            created_at=datetime.fromisoformat(snapshot["source_created_at"]),
        )
        session.add(source)
        await session.flush()
        for model in LINKED:
            moved = [
                uuid.UUID(key)
                for key, value in snapshot["links"][model.__tablename__].items()
                if value == str(audit.source_id)
            ]
            if moved:
                await session.execute(
                    update(model).where(model.id.in_(moved)).values(client_id=audit.source_id)
                )
        for key, value in snapshot["manual_assignments"].items():
            if snapshot["links"]["conversations"][key] == str(audit.source_id):
                await session.execute(
                    update(Conversation)
                    .where(Conversation.id == uuid.UUID(key))
                    .values(client_assignment_manual=value)
                )
        await session.execute(
            update(Client).where(Client.id == audit.target_id).values(**snapshot["target"])
        )
        audit.snapshot = {**snapshot, "undone_at": datetime.now(UTC).isoformat()}
        await session.commit()
        return {"source_id": str(audit.source_id), "target_id": str(audit.target_id)}
    except Exception:
        await session.rollback()
        raise
