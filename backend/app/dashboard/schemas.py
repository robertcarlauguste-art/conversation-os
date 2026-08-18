from typing import Literal

from pydantic import BaseModel, Field

from app.client.schemas import ClientListItem
from app.conversation.schemas import ConversationListItem


class DashboardOverview(BaseModel):
    clients: int
    conversations: int
    completed: int
    processing: int
    failed: int


class DashboardPriority(BaseModel):
    rank: int = Field(ge=1)
    severity: Literal["critical", "high", "medium"]
    category: Literal["processing", "followup"]
    title: str
    description: str
    href: str | None = None


class DashboardResponse(BaseModel):
    overview: DashboardOverview
    recent_clients: list[ClientListItem]
    recent_conversations: list[ConversationListItem]
    priorities: list[DashboardPriority]
    alerts: list[str]
    followups: list[str]
