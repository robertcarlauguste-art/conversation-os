"""
Shared API response envelope.

Every slice's API responses follow the same `{"success": ..., "data": ...}`
shape (per the Sprint 1 spec's POST /conversations response). Defining
it once here means a future slice doesn't reinvent — or subtly
diverge from — the same envelope.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel

DataT = TypeVar("DataT")


class ApiResponse(BaseModel, Generic[DataT]):
    success: bool
    data: DataT


class ApiError(BaseModel):
    success: bool = False
    error: str
    detail: str | None = None
