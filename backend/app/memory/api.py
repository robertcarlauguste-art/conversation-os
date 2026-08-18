"""
Memory API routes. Read-only — memories are created by the
orchestrator's pipeline, not via a direct API call.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.memory.repository import MemoryRepository
from app.memory.schemas import ActionItemOut, MemoryDetail, MemoryListItem
from app.memory.service import ActionItemNotFoundError, ActionItemService
from app.schemas.envelope import ApiResponse

router = APIRouter(prefix="/memories", tags=["memories"])


@router.post(
    "/action-items/{action_item_id}/complete",
    response_model=ApiResponse[ActionItemOut],
)
async def complete_action_item(
    action_item_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ActionItemOut]:
    service = ActionItemService(MemoryRepository(session))
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
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ActionItemOut]:
    service = ActionItemService(MemoryRepository(session))
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
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[list[MemoryListItem]]:
    repository = MemoryRepository(session)
    memories = await repository.list_all()
    return ApiResponse(success=True, data=[MemoryListItem.model_validate(m) for m in memories])


@router.get("/by-conversation/{conversation_id}", response_model=ApiResponse[MemoryDetail])
async def get_memory_by_conversation(
    conversation_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[MemoryDetail]:
    repository = MemoryRepository(session)
    memory = await repository.get_by_conversation_id(conversation_id)
    if memory is None:
        raise HTTPException(
            status_code=404, detail=f"No memory found for conversation {conversation_id}."
        )
    return ApiResponse(success=True, data=MemoryDetail.model_validate(memory))


@router.get("/{memory_id}", response_model=ApiResponse[MemoryDetail])
async def get_memory(
    memory_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[MemoryDetail]:
    repository = MemoryRepository(session)
    memory = await repository.get(memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found.")
    return ApiResponse(success=True, data=MemoryDetail.model_validate(memory))
