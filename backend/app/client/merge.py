"""Explicit, owner-scoped client merge with a durable pre-merge snapshot."""

import hashlib
import json

from fastapi import HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.orm import noload

from app.client.models import Client, ClientFact, ClientMergeAudit
from app.conversation.models import Conversation
from app.dashboard.models import ClientFollowupAction
from app.memory.models import Memory, Person


def profile(client):
    return {
        key: getattr(client, key) for key in ("full_name", "email", "phone", "role", "saved_review")
    }


async def inspect_merge(session, owner_id, source_id, target_id):
    # Ordered row locks serialize overlapping merges and block new FK references.
    records = (
        (
            await session.execute(
                select(Client)
                .options(noload("*"))
                .where(Client.owner_id == owner_id, Client.id.in_([source_id, target_id]))
                .order_by(Client.id)
                .with_for_update()
            )
        )
        .scalars()
        .all()
    )
    if len(records) != 2:
        raise HTTPException(404, "Client pair not found.")
    by_id = {client.id: client for client in records}
    source, target = by_id[source_id], by_id[target_id]
    snapshot = {"source": profile(source), "target": profile(target), "links": {}}
    for model in (Conversation, Person, ClientFact, ClientFollowupAction):
        rows = (
            (
                await session.execute(
                    select(model)
                    .options(noload("*"))
                    .where(model.client_id.in_([source_id, target_id]))
                    .with_for_update()
                )
            )
            .scalars()
            .all()
        )
        for row in rows:
            if isinstance(row, Conversation):
                if row.owner_id != owner_id:
                    raise HTTPException(409, "Client links need review before merging.")
                if row.status.value not in ("COMPLETED", "FAILED"):
                    raise HTTPException(409, "Wait for linked recordings to finish processing.")
            elif isinstance(row, (Person, ClientFact)):
                memory_id = row.memory_id if isinstance(row, Person) else row.source_memory_id
                owned = await session.scalar(
                    select(Memory.id)
                    .join(Conversation, Memory.conversation_id == Conversation.id)
                    .where(Memory.id == memory_id, Conversation.owner_id == owner_id)
                )
                if owned is None:
                    raise HTTPException(409, "Client links need review before merging.")
                if isinstance(row, ClientFact):
                    owned_source = await session.scalar(
                        select(Conversation.id).where(
                            Conversation.id == row.source_conversation_id,
                            Conversation.owner_id == owner_id,
                        )
                    )
                    if owned_source is None:
                        raise HTTPException(409, "Client links need review before merging.")
        snapshot["links"][model.__tablename__] = {
            str(row.id): str(row.client_id) for row in sorted(rows, key=lambda row: str(row.id))
        }
    encoded = json.dumps(snapshot, sort_keys=True, default=str).encode()
    token = hashlib.sha256(encoded).hexdigest()
    counts = {
        table: sum(value == str(source_id) for value in links.values())
        for table, links in snapshot["links"].items()
    }
    return source, target, snapshot, token, counts


async def merge_clients(session, owner_id, source_id, target_id, expected_token, confirmed_name):
    try:
        source, target, snapshot, token, counts = await inspect_merge(
            session, owner_id, source_id, target_id
        )
        if token != expected_token or confirmed_name != target.full_name:
            raise HTTPException(409, "Client details changed. Review the merge again.")
        session.add(
            ClientMergeAudit(
                owner_id=owner_id, source_id=source_id, target_id=target_id, snapshot=snapshot
            )
        )
        for model in (Conversation, Person, ClientFact, ClientFollowupAction):
            values = {"client_id": target_id}
            if model is Conversation:
                values["client_assignment_manual"] = True
            await session.execute(
                update(model).where(model.client_id == source_id).values(**values)
            )
        # Old reviews describe separate histories; archive both, never present either as current.
        target.saved_review = None
        await session.flush()
        # Bulk delete avoids ORM relationship cascades; children now point at the retained record.
        await session.execute(
            delete(Client).where(Client.id == source_id, Client.owner_id == owner_id)
        )
        await session.commit()
        return {"client_id": str(target_id), "moved": counts}
    except Exception:
        await session.rollback()
        raise
