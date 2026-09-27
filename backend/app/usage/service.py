"""Durable, owner-scoped pilot admission. Caller commits or rolls back admission."""

from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

LIMITS = {
    "recordings": 30,
    "storage_bytes": 250 * 1024 * 1024,
    "uploads": 5,
    "audio_seconds": 900,
    "ai": 5,
    "retries": 2,
}


class UsageService:
    def __init__(self, session: AsyncSession, owner_id: str):
        self.session = session
        self.owner_id = owner_id

    async def lock(self):
        # Serialize admissions across every API process, independently per owner.
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:owner, 0))"),
            {"owner": "pilot:" + self.owner_id},
        )

    async def snapshot(self):
        day = await self.session.scalar(text("SELECT (clock_timestamp() AT TIME ZONE 'UTC')::date"))
        daily = (
            (
                await self.session.execute(
                    text(
                        "SELECT uploads, audio_seconds, ai, retries FROM pilot_usage "
                        "WHERE owner_id=:owner AND day=:day"
                    ),
                    {"owner": self.owner_id, "day": day},
                )
            )
            .mappings()
            .first()
        )
        active = (
            (
                await self.session.execute(
                    text(
                        "SELECT count(*) AS recordings, "
                        "coalesce(sum(file_size),0) AS storage_bytes "
                        "FROM conversations WHERE owner_id=:owner"
                    ),
                    {"owner": self.owner_id},
                )
            )
            .mappings()
            .one()
        )
        used = {
            **dict(active),
            **(dict(daily) if daily else dict(uploads=0, audio_seconds=0, ai=0, retries=0)),
        }
        return {
            "enabled": True,
            "used": used,
            "limits": LIMITS,
            "remaining": {k: max(0, v - used[k]) for k, v in LIMITS.items()},
            "resets_at": (day + timedelta(days=1)).isoformat() + "T00:00:00Z",
        }

    async def admit(self, kind: str, *, size: int = 0, seconds: int = 0):
        if kind not in ("uploads", "ai", "retries"):
            raise ValueError("Unknown allowance")
        await self.lock()
        state = await self.snapshot()
        changes = {kind: 1}
        if kind == "uploads":
            changes.update(recordings=1, storage_bytes=size, audio_seconds=seconds)
        for key, amount in changes.items():
            if state["used"][key] + amount > LIMITS[key]:
                message = (
                    "Your pilot storage allowance is full. "
                    "Delete an unneeded recording to make room."
                    if key in ("recordings", "storage_bytes")
                    else "You've used today's pilot allowance. Saved notes remain available. "
                    "Try again after " + state["resets_at"] + "."
                )
                raise HTTPException(429, message)
        # Column names come only from the fixed allowlist above.
        day = date.fromisoformat(state["resets_at"][:10]) - timedelta(days=1)
        await self.session.execute(
            text(
                "INSERT INTO pilot_usage(owner_id, day) VALUES (:owner, :day) "
                "ON CONFLICT DO NOTHING"
            ),
            {"owner": self.owner_id, "day": day},
        )
        await self.session.execute(
            text(
                f"UPDATE pilot_usage SET {kind}={kind}+1, audio_seconds=audio_seconds+:seconds "
                "WHERE owner_id=:owner AND day=:day"
            ),
            {"owner": self.owner_id, "seconds": seconds, "day": day},
        )

    async def consume_ai(self):
        await self.admit("ai")
        # Persist before contacting the provider. Provider errors still cost usage.
        await self.session.commit()
