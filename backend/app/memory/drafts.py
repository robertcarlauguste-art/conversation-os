import uuid
from datetime import datetime
from typing import Literal

from fastapi import HTTPException
from pydantic import Field, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.followup import FollowupDraft

Channel = Literal["email", "text"]


class SaveDraft(FollowupDraft):
    expected_version: int = Field(ge=0)

    @field_validator("body")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Write a message before saving.")
        return value


class SavedDraft(FollowupDraft):
    channel: Channel
    version: int
    updated_at: datetime


class DraftRepository:
    def __init__(self, session: AsyncSession, owner_id: str):
        self.session = session
        self.owner_id = owner_id

    async def owned(self, conversation_id: uuid.UUID, *, lock: bool = False):
        # A parent lock serializes first saves as well as updates and deletion.
        found = await self.session.scalar(
            text(
                "SELECT id FROM conversations WHERE id=:id AND owner_id=:owner"
                + (" FOR UPDATE" if lock else "")
            ),
            {"id": conversation_id, "owner": self.owner_id},
        )
        if found is None:
            raise HTTPException(404, "Conversation not found.")

    async def get(self, conversation_id: uuid.UUID, channel: Channel) -> SavedDraft | None:
        await self.owned(conversation_id)
        result = await self.session.execute(
            text(
                "SELECT d.subject,d.body,d.channel,d.version,d.updated_at FROM followup_drafts d "
                "JOIN conversations c ON c.id=d.conversation_id "
                "WHERE c.id=:id AND c.owner_id=:owner AND d.channel=:channel"
            ),
            {"id": conversation_id, "owner": self.owner_id, "channel": channel},
        )
        row = result.mappings().first()
        return SavedDraft.model_validate(dict(row)) if row else None

    async def save(
        self, conversation_id: uuid.UUID, channel: Channel, body: SaveDraft
    ) -> SavedDraft:
        await self.owned(conversation_id, lock=True)
        existing = await self.get(conversation_id, channel)
        version = existing.version if existing else 0
        if version != body.expected_version:
            raise HTTPException(
                409,
                "This draft changed in another tab. Copy your edits before "
                "reopening the saved draft.",
            )
        await self.session.execute(
            text(
                "INSERT INTO followup_drafts(conversation_id,channel,subject,body,version) "
                "VALUES (:id,:channel,:subject,:body,:version) "
                "ON CONFLICT (conversation_id,channel) DO UPDATE SET subject=EXCLUDED.subject, "
                "body=EXCLUDED.body,version=EXCLUDED.version,updated_at=now()"
            ),
            {
                "id": conversation_id,
                "channel": channel,
                "subject": body.subject if channel == "email" else "",
                "body": body.body,
                "version": version + 1,
            },
        )
        saved = await self.get(conversation_id, channel)
        assert saved is not None
        await self.session.commit()
        return saved
