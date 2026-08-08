"""
Memory API routes. Read-only — memories are created by the
orchestrator's pipeline, not via a direct API call.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.memory.repository import MemoryRepository
from app.memory.schemas import MemoryDetail, MemoryListItem
from app.schemas.envelope import ApiResponse

router = APIRouter(prefix="/memories", tags=["memories"])


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
