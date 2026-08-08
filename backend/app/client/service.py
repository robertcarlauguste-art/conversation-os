"""
Client service.

Owns the FD-003 matching decision and FD-005 provenance requirement.
Called by the orchestrator's reconciliation stage — this service has
no knowledge of transcription or the AI pipeline, only of names,
roles, and facts handed to it.
"""

import logging
import uuid

from app.client.events import emit_client_created, emit_client_matched, emit_client_profile_updated
from app.client.models import Client, ClientFact
from app.client.repository import ClientRepository
from app.client.validators import validate_fact_text
from app.services.base import BaseService

logger = logging.getLogger("conversation_os.client")


class ClientNotFoundError(Exception):
    pass


class ClientService(BaseService[ClientRepository]):
    async def find_or_create(
        self, *, name: str, role: str | None, conversation_id: uuid.UUID
    ) -> tuple[Client, bool]:
        """
        FD-003: deterministic, high-precision matching. Returns
        (client, was_created). A match requires exact name AND exact
        role — role missing on either side means no automatic match
        is possible, and a new Client is created rather than guessed
        at. This is the intended, conservative behavior of "never
        auto-merge on name alone," not a bug: without a role (or,
        in a future sprint, an email/phone), there is no corroborating
        attribute to check, so no automatic reconciliation happens.
        """
        normalized_name = name.strip().lower()
        normalized_role = (role or "").strip().lower()

        if normalized_role:
            existing = await self.repository.find_corroborated_match(
                normalized_name, normalized_role
            )
            if existing is not None:
                emit_client_matched(existing.id, conversation_id)
                logger.info(
                    "client_matched client_id=%s conversation_id=%s", existing.id, conversation_id
                )
                return existing, False

        client = Client(full_name=name.strip(), role=role)
        await self.repository.add(client)
        await self.repository.commit()
        emit_client_created(client.id, conversation_id)
        logger.info("client_created client_id=%s conversation_id=%s", client.id, conversation_id)
        return client, True

    async def record_facts(
        self,
        *,
        client_id: uuid.UUID,
        fact_texts: list[str],
        source_conversation_id: uuid.UUID,
        source_memory_id: uuid.UUID,
        confidence: float | None,
    ) -> list[ClientFact]:
        """FD-005: every fact carries provenance — never optional."""
        facts: list[ClientFact] = []
        for text in fact_texts:
            validate_fact_text(text)
            facts.append(
                ClientFact(
                    client_id=client_id,
                    fact_text=text.strip(),
                    source_conversation_id=source_conversation_id,
                    source_memory_id=source_memory_id,
                    confidence=confidence,
                )
            )
        for fact in facts:
            self.repository.session.add(fact)
        await self.repository.commit()

        if facts:
            emit_client_profile_updated(client_id, source_conversation_id, len(facts))
        return facts

    async def get_client(self, client_id: uuid.UUID) -> Client:
        client = await self.repository.get_with_facts(client_id)
        if client is None:
            raise ClientNotFoundError(f"Client {client_id} not found.")
        return client

    async def list_clients(self) -> list[Client]:
        return await self.repository.list_all()
