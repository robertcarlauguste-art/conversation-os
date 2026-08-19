"""
Client API routes.

Read-only endpoints for CRM clients plus manual conversation linking.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.client.repository import ClientRepository
from app.client.schemas import (
    ClientConversationItem,
    ClientDetail,
    ClientListItem,
)
from app.client.service import (
    ClientNotFoundError,
    ClientService,
)
from app.conversation.repository import ConversationRepository
from app.core.database import get_db_session
from app.schemas.envelope import ApiResponse

router = APIRouter(
    prefix="/clients",
    tags=["clients"],
)


def get_client_service(
    session: AsyncSession = Depends(get_db_session),
) -> ClientService:
    return ClientService(ClientRepository(session))


@router.get(
    "",
    response_model=ApiResponse[list[ClientListItem]],
)
async def list_clients(
    service: ClientService = Depends(get_client_service),
) -> ApiResponse[list[ClientListItem]]:

    clients = await service.list_client_profiles()

    return ApiResponse(
        success=True,
        data=[ClientListItem.model_validate(client) for client in clients],
    )


@router.get(
    "/{client_id}",
    response_model=ApiResponse[ClientDetail],
)
async def get_client(
    client_id: uuid.UUID,
    service: ClientService = Depends(get_client_service),
) -> ApiResponse[ClientDetail]:

    try:
        client = await service.get_profile(client_id)

    except ClientNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    return ApiResponse(
        success=True,
        data=ClientDetail.model_validate(client),
    )


@router.get(
    "/{client_id}/conversations",
    response_model=ApiResponse[list[ClientConversationItem]],
)
async def get_client_conversations(
    client_id: uuid.UUID,
    service: ClientService = Depends(get_client_service),
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[list[ClientConversationItem]]:

    try:
        await service.get_profile(client_id)

    except ClientNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    conversation_repo = ConversationRepository(session)

    conversations = await conversation_repo.list_by_client_id(client_id)

    return ApiResponse(
        success=True,
        data=[
            ClientConversationItem(
                id=c.id,
                title=c.title,
                filename=c.filename,
                status=c.status.value,
                created_at=c.created_at,
            )
            for c in conversations
        ],
    )


@router.post(
    "/{client_id}/conversations/{conversation_id}",
    status_code=204,
)
async def link_conversation(
    client_id: uuid.UUID,
    conversation_id: uuid.UUID,
    service: ClientService = Depends(get_client_service),
    session: AsyncSession = Depends(get_db_session),
) -> None:

    try:
        await service.get_profile(client_id)

    except ClientNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    conversation_repo = ConversationRepository(session)

    conversation = await conversation_repo.get(conversation_id)

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation {conversation_id} not found.",
        )

    conversation.client_id = client_id

    await conversation_repo.commit()


@router.delete(
    "/{client_id}/conversations/{conversation_id}",
    status_code=204,
)
async def unlink_conversation(
    client_id: uuid.UUID,
    conversation_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> None:

    conversation_repo = ConversationRepository(session)

    conversation = await conversation_repo.get(conversation_id)

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation {conversation_id} not found.",
        )

    if conversation.client_id != client_id:
        raise HTTPException(
            status_code=404,
            detail="This conversation is not linked to this client.",
        )

    conversation.client_id = None

    await conversation_repo.commit()
