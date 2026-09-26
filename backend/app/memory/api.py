"""
Memory reads and owner-scoped corrections. Memories are created by the
orchestrator's pipeline; users can correct existing decisions and tasks.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal
from app.core.database import get_db_session
from app.memory.models import ActionItem, Decision
from app.memory.repository import MemoryRepository
from app.memory.schemas import (
    ActionItemEdit,
    ActionItemOut,
    DecisionEdit,
    DecisionOut,
    MemoryDetail,
    MemoryListItem,
)
from app.memory.service import ActionItemNotFoundError, ActionItemService
from app.schemas.envelope import ApiResponse

router = APIRouter(prefix="/memories", tags=["memories"])


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
