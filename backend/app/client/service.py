"""
Client service.

Owns the FD-003 matching decision and FD-005 provenance requirement.

Called by the orchestrator reconciliation stage.

Responsibilities:
- deterministic client matching
- client creation
- provenance tracking
- preventing non-client entities from becoming clients
- canonical role normalization
"""

import logging
import uuid

from app.client.events import (
    emit_client_created,
    emit_client_matched,
    emit_client_profile_updated,
)
from app.client.models import (
    Client,
    ClientFact,
)
from app.client.repository import ClientRepository
from app.client.validators import validate_fact_text
from app.memory.models import PersonType
from app.services.base import BaseService

logger = logging.getLogger("conversation_os.client")


class ClientNotFoundError(Exception):
    pass


class InvalidClientEntityError(Exception):
    """
    Raised when attempting to create a client
    from a non-client entity.
    """

    pass


class ClientService(BaseService[ClientRepository]):
    def _normalize_role(
        self,
        role: str | None,
    ) -> str | None:
        """
        Convert AI extracted role variations into
        canonical CRM roles.
        """

        if not role:
            return None

        value = role.strip().lower()

        mappings = {
            # Client variations
            "home buyer": "buyer",
            "homebuyer": "buyer",
            "home buyer/client": "buyer",
            "buyer": "buyer",
            "customer": "buyer",
            "client": "buyer",
            # Agent variations
            "realtor": "agent",
            "real estate agent": "agent",
            "broker": "agent",
            "salesperson": "agent",
        }

        for key, canonical in mappings.items():
            if key in value:
                return canonical

        return value

    async def find_or_create(
        self,
        *,
        name: str,
        role: str | None,
        entity_type: PersonType,
        conversation_id: uuid.UUID,
    ) -> tuple[Client, bool]:
        """
        FD-003

        Deterministic client matching.

        Only CLIENT entities may become CRM clients.
        """

        if entity_type != PersonType.CLIENT:
            logger.info(
                "client_reconciliation_skipped " "name=%s entity_type=%s",
                name,
                entity_type,
            )

            raise InvalidClientEntityError(f"{entity_type} cannot become a client")

        normalized_name = name.strip().lower()
        normalized_role = self._normalize_role(role)

        if normalized_role:
            existing = await self.repository.find_corroborated_match(
                normalized_name,
                normalized_role,
            )

            if existing is not None:
                emit_client_matched(
                    existing.id,
                    conversation_id,
                )

                logger.info(
                    "client_matched " "client_id=%s conversation_id=%s",
                    existing.id,
                    conversation_id,
                )

                return existing, False

        client = Client(
            owner_id=self.repository.owner_id,
            full_name=name.strip(),
            role=normalized_role,
        )

        await self.repository.add(client)
        await self.repository.commit()

        emit_client_created(
            client.id,
            conversation_id,
        )

        logger.info(
            "client_created " "client_id=%s conversation_id=%s",
            client.id,
            conversation_id,
        )

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
        """
        FD-005

        Every client fact retains provenance.
        """

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
            emit_client_profile_updated(
                client_id,
                source_conversation_id,
                len(facts),
            )

        return facts

    #
    # Sprint 4
    #

    async def get_profile(
        self,
        client_id: uuid.UUID,
    ) -> Client:
        """
        Returns one client with all related objects eagerly loaded.
        """

        client = await self.repository.get_with_facts(client_id)

        if client is None:
            raise ClientNotFoundError(f"Client {client_id} not found.")

        return client

    async def list_client_profiles(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
        search: str | None = None,
        role: str | None = None,
    ) -> list[Client]:
        """
        Returns all clients.
        """

        return await self.repository.list_all(
            limit=limit,
            offset=offset,
            search=search,
            role=role,
        )

    #
    # Backwards compatibility
    #

    async def get_client(
        self,
        client_id: uuid.UUID,
    ) -> Client:
        return await self.get_profile(client_id)

    async def list_clients(
        self,
    ) -> list[Client]:
        return await self.list_client_profiles()
