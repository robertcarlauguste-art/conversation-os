import asyncio
import uuid

from sqlalchemy import update, delete

from app.core.database import AsyncSessionLocal
from app.client.models import Client, ClientFact
from app.memory.models import Person
from app.conversation.models import Conversation


CANONICAL_JOHN = uuid.UUID(
    "235db2e0-fb70-4070-a3ce-aed266213c64"
)

OLD_JOHNS = [
    uuid.UUID("2260b0fd-cd1e-4bf5-a49b-e7e1f6f96e30"),
    uuid.UUID("87e8310b-5ead-40f6-aee8-1505f8ba4421"),
    uuid.UUID("0b6912d5-6491-44fd-b6cc-d916f3fdd271"),
]

SARAH = uuid.UUID(
    "e8b0d79a-327a-4530-8d35-b910c973f4f4"
)


async def cleanup():

    async with AsyncSessionLocal() as session:

        print("Migrating people...")

        await session.execute(
            update(Person)
            .where(Person.client_id.in_(OLD_JOHNS))
            .values(client_id=CANONICAL_JOHN)
        )


        print("Migrating conversations...")

        await session.execute(
            update(Conversation)
            .where(
                Conversation.client_id.in_(OLD_JOHNS)
            )
            .values(client_id=CANONICAL_JOHN)
        )


        print("Migrating facts...")

        await session.execute(
            update(ClientFact)
            .where(
                ClientFact.client_id.in_(OLD_JOHNS)
            )
            .values(client_id=CANONICAL_JOHN)
        )


        print("Removing Sarah facts...")

        await session.execute(
            delete(ClientFact)
            .where(
                ClientFact.client_id == SARAH
            )
        )


        print("Deleting old clients...")

        await session.execute(
            delete(Client)
            .where(
                Client.id.in_(
                    OLD_JOHNS + [SARAH]
                )
            )
        )


        print("Removing orphan UNKNOWN people...")


        await session.execute(
            delete(Person)
            .where(
                Person.entity_type == "UNKNOWN"
            )
        )


        await session.commit()


        print("Cleanup complete")


asyncio.run(cleanup())