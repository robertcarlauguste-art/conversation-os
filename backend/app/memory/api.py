"""
Memory reads and owner-scoped corrections. Memories are created by the
orchestrator's pipeline; users can correct existing decisions and tasks.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal
from app.conversation.enums import ConversationStatus
from app.conversation.repository import ConversationRepository
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.memory.drafts import Channel, DraftRepository, SavedDraft, SaveDraft
from app.memory.followup import FollowupDraft, FollowupRequest, generate_draft, selected_facts
from app.memory.models import ActionItem, Decision
from app.memory.repository import MemoryRepository
from app.memory.schemas import (
    ActionItemEdit,
    ActionItemOut,
    DecisionEdit,
    DecisionOut,
    MemoryDetail,
    MemoryListItem,
    PersonOut,
)
from app.memory.service import ActionItemNotFoundError, ActionItemService
from app.providers.dependencies import get_ai_provider
from app.schemas.envelope import ApiResponse
from app.usage.service import UsageService

router = APIRouter(prefix="/memories", tags=["memories"])


class PersonConfirmation(BaseModel):
    client_id: uuid.UUID | None


@router.put("/{memory_id}/people/{person_id}/confirmation", response_model=ApiResponse[PersonOut])
async def confirm_person(
    memory_id: uuid.UUID,
    person_id: uuid.UUID,
    body: PersonConfirmation,
    principal: CurrentPrincipal,
    session: AsyncSession = Depends(get_db_session),
):
    person = await MemoryRepository(session, principal.user_id).confirm_person(
        memory_id, person_id, body.client_id
    )
    if person is None:
        raise HTTPException(404, "Person or client not found.")
    return ApiResponse(success=True, data=PersonOut.model_validate(person))


@router.get(
    "/by-conversation/{conversation_id}/drafts/{channel}",
    response_model=ApiResponse[SavedDraft | None],
)
async def read_saved_draft(
    conversation_id: uuid.UUID,
    channel: Channel,
    principal: CurrentPrincipal,
    session: AsyncSession = Depends(get_db_session),
):
    draft = await DraftRepository(session, principal.user_id).get(conversation_id, channel)
    return ApiResponse(success=True, data=draft)


@router.put(
    "/by-conversation/{conversation_id}/drafts/{channel}", response_model=ApiResponse[SavedDraft]
)
async def save_followup_draft(
    conversation_id: uuid.UUID,
    channel: Channel,
    body: SaveDraft,
    principal: CurrentPrincipal,
    session: AsyncSession = Depends(get_db_session),
):
    draft = await DraftRepository(session, principal.user_id).save(conversation_id, channel, body)
    return ApiResponse(success=True, data=draft)


@router.post(
    "/by-conversation/{conversation_id}/follow-up", response_model=ApiResponse[FollowupDraft]
)
async def prepare_followup(
    conversation_id: uuid.UUID,
    body: FollowupRequest,
    principal: CurrentPrincipal,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> ApiResponse[FollowupDraft]:
    conversation = await ConversationRepository(session, principal.user_id).get(conversation_id)
    if conversation is None:
        raise HTTPException(404, "Conversation results not found.")
    if conversation.status != ConversationStatus.COMPLETED:
        raise HTTPException(409, "Wait until this conversation finishes processing.")
    memory = await MemoryRepository(session, principal.user_id).get_by_conversation_id(
        conversation_id
    )
    if memory is None:
        raise HTTPException(404, "Conversation results not found.")
    facts = selected_facts(memory, body)
    if not settings.anthropic_api_key:
        raise HTTPException(503, "Drafting is temporarily unavailable.")
    if settings.pilot_limits_enabled:
        await UsageService(session, principal.user_id).consume_ai()
    draft = await generate_draft(get_ai_provider(settings), body.channel, facts)
    return ApiResponse(success=True, data=draft)


@router.patch("/{memory_id}/action-items/{item_id}", response_model=ApiResponse[ActionItemOut])
async def edit_action_item(
    memory_id: uuid.UUID,
    item_id: uuid.UUID,
    body: ActionItemEdit,
    principal: CurrentPrincipal,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ActionItemOut]:
    item = await MemoryRepository(session, principal.user_id).edit_item(
        memory_id, item_id, ActionItem, body.model_dump()
    )
    if item is None:
        raise HTTPException(404, "Item not found.")
    return ApiResponse(success=True, data=ActionItemOut.model_validate(item))


@router.patch("/{memory_id}/decisions/{item_id}", response_model=ApiResponse[DecisionOut])
async def edit_decision(
    memory_id: uuid.UUID,
    item_id: uuid.UUID,
    body: DecisionEdit,
    principal: CurrentPrincipal,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[DecisionOut]:
    item = await MemoryRepository(session, principal.user_id).edit_item(
        memory_id, item_id, Decision, body.model_dump()
    )
    if item is None:
        raise HTTPException(404, "Item not found.")
    return ApiResponse(success=True, data=DecisionOut.model_validate(item))


@router.post(
    "/action-items/{action_item_id}/complete",
    response_model=ApiResponse[ActionItemOut],
)
async def complete_action_item(
    action_item_id: uuid.UUID,
    principal: CurrentPrincipal,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ActionItemOut]:
    service = ActionItemService(MemoryRepository(session, principal.user_id))
    try:
        action_item = await service.complete(action_item_id)
    except ActionItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiResponse(
        success=True,
        data=ActionItemOut.model_validate(action_item),
    )


@router.post(
    "/action-items/{action_item_id}/reopen",
    response_model=ApiResponse[ActionItemOut],
)
async def reopen_action_item(
    action_item_id: uuid.UUID,
    principal: CurrentPrincipal,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ActionItemOut]:
    service = ActionItemService(MemoryRepository(session, principal.user_id))
    try:
        action_item = await service.reopen(action_item_id)
    except ActionItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiResponse(
        success=True,
        data=ActionItemOut.model_validate(action_item),
    )


@router.get("", response_model=ApiResponse[list[MemoryListItem]])
async def list_memories(
    principal: CurrentPrincipal,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[list[MemoryListItem]]:
    repository = MemoryRepository(session, principal.user_id)
    memories = await repository.list_all()
    return ApiResponse(success=True, data=[MemoryListItem.model_validate(m) for m in memories])


@router.get("/by-conversation/{conversation_id}", response_model=ApiResponse[MemoryDetail])
async def get_memory_by_conversation(
    conversation_id: uuid.UUID,
    principal: CurrentPrincipal,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[MemoryDetail]:
    repository = MemoryRepository(session, principal.user_id)
    memory = await repository.get_by_conversation_id(conversation_id)
    if memory is None:
        raise HTTPException(
            status_code=404, detail=f"No memory found for conversation {conversation_id}."
        )
    return ApiResponse(success=True, data=MemoryDetail.model_validate(memory))


@router.get("/{memory_id}", response_model=ApiResponse[MemoryDetail])
async def get_memory(
    memory_id: uuid.UUID,
    principal: CurrentPrincipal,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[MemoryDetail]:
    repository = MemoryRepository(session, principal.user_id)
    memory = await repository.get(memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found.")
    return ApiResponse(success=True, data=MemoryDetail.model_validate(memory))
