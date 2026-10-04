"""
Client API routes.

Read-only endpoints for CRM clients plus manual conversation linking.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal
from app.client.repository import ClientRepository
from app.client.schemas import (
    ClientConversationItem,
    ClientCreate,
    ClientDetail,
    ClientListItem,
)
from app.client.service import (
    ClientNotFoundError,
    ClientService,
)
from app.conversation.repository import ConversationRepository
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.schemas.envelope import ApiResponse

router = APIRouter(
    prefix="/clients",
    tags=["clients"],
)


def get_client_service(
    principal: CurrentPrincipal,
    session: AsyncSession = Depends(get_db_session),
) -> ClientService:
    return ClientService(ClientRepository(session, principal.user_id))


@router.post("", response_model=ApiResponse[ClientListItem], status_code=201)
async def create_client(
    body: ClientCreate,
    service: ClientService = Depends(get_client_service),
) -> ApiResponse[ClientListItem]:
    client = await service.create_named_client(body.full_name)
    return ApiResponse(success=True, data=ClientListItem.model_validate(client))


@router.get(
    "",
    response_model=ApiResponse[list[ClientListItem]],
)
async def list_clients(
    service: ClientService = Depends(get_client_service),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    role: str | None = Query(default=None, min_length=1, max_length=64),
) -> ApiResponse[list[ClientListItem]]:

    clients = await service.list_client_profiles(
        limit=limit,
        offset=offset,
        search=search,
        role=role,
    )

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
    principal: CurrentPrincipal,
    search: str | None = Query(default=None, max_length=100),
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

    conversation_repo = ConversationRepository(session, principal.user_id)

    conversations = await conversation_repo.list_client_previews(client_id, search)

    return ApiResponse(
        success=True,
        data=[
            ClientConversationItem(
                id=c.id,
                title=c.title,
                filename=c.filename,
                summary_preview=(summary[:300].strip() if summary else None),
                status=c.status.value,
                created_at=c.created_at,
            )
            for c, summary in conversations
        ],
    )


@router.post(
    "/{client_id}/conversations/{conversation_id}",
    status_code=204,
)
async def link_conversation(
    client_id: uuid.UUID,
    conversation_id: uuid.UUID,
    principal: CurrentPrincipal,
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

    conversation_repo = ConversationRepository(session, principal.user_id)

    conversation = await conversation_repo.get(conversation_id)

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation {conversation_id} not found.",
        )

    conversation.client_id = client_id
    conversation.client_assignment_manual = True

    await conversation_repo.commit()


@router.delete(
    "/{client_id}/conversations/{conversation_id}",
    status_code=204,
)
async def unlink_conversation(
    client_id: uuid.UUID,
    conversation_id: uuid.UUID,
    principal: CurrentPrincipal,
    service: ClientService = Depends(get_client_service),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    try:
        await service.get_profile(client_id)
    except ClientNotFoundError:
        raise HTTPException(404, "Client not found.") from None
    conversation_repo = ConversationRepository(session, principal.user_id)

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
    conversation.client_assignment_manual = True

    await conversation_repo.commit()


@router.post("/{client_id}/review")
async def review_client_updates(
    client_id: uuid.UUID,
    principal: CurrentPrincipal,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
):
    from app.client.review import generate_review
    from app.providers.dependencies import get_ai_provider

    repository = ClientRepository(session, principal.user_id)
    if await repository.get(client_id) is None:
        raise HTTPException(404, "Client not found.")
    try:
        provider = get_ai_provider(settings)
    except RuntimeError:
        raise HTTPException(503, "Client review is currently unavailable.") from None
    from app.usage.service import UsageService

    allowance = UsageService(session, principal.user_id) if settings.pilot_limits_enabled else None
    return ApiResponse(
        success=True,
        data=await generate_review(
            repository,
            client_id,
            provider,
            before_provider=allowance.consume_ai if allowance else None,
        ),
    )


@router.get("/{client_id}/review")
async def get_saved_client_review(
    client_id: uuid.UUID,
    principal: CurrentPrincipal,
    session: AsyncSession = Depends(get_db_session),
):
    from app.client.review import load_review

    return ApiResponse(
        success=True,
        data=await load_review(ClientRepository(session, principal.user_id), client_id),
    )


class MergePreviewRequest(BaseModel):
    target_id: uuid.UUID


class MergeRequest(MergePreviewRequest):
    expected_token: str = Field(min_length=64, max_length=64)
    confirmed_name: str = Field(min_length=1, max_length=255)


@router.post("/{client_id}/merge-preview")
async def preview_client_merge(
    client_id: uuid.UUID,
    body: MergePreviewRequest,
    principal: CurrentPrincipal,
    session: AsyncSession = Depends(get_db_session),
):
    from app.client.merge import inspect_merge

    try:
        source, target, snapshot, token, counts = await inspect_merge(
            session, principal.user_id, client_id, body.target_id
        )
        return ApiResponse(
            success=True,
            data={
                "source": {k: v for k, v in snapshot["source"].items() if k != "saved_review"},
                "target": {k: v for k, v in snapshot["target"].items() if k != "saved_review"},
                "token": token,
                "moved": counts,
            },
        )
    finally:
        await session.rollback()


@router.post("/{client_id}/merge")
async def confirm_client_merge(
    client_id: uuid.UUID,
    body: MergeRequest,
    principal: CurrentPrincipal,
    session: AsyncSession = Depends(get_db_session),
):
    from app.client.merge import merge_clients

    return ApiResponse(
        success=True,
        data=await merge_clients(
            session,
            principal.user_id,
            client_id,
            body.target_id,
            body.expected_token,
            body.confirmed_name,
        ),
    )
