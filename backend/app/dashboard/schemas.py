import uuid
from datetime import datetime
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


class DashboardBriefItem(BaseModel):
    category: Literal[
        "conversations",
        "processing",
        "attention",
        "clients",
        "followups",
    ]
    text: str
    tone: Literal["neutral", "positive", "warning"]


class DashboardAIBriefing(BaseModel):
    content: str
    source: Literal["ai", "deterministic"]
    model: str | None = None
    fallback_reason: Literal["not_configured", "provider_error"] | None = None
    generated_at: datetime


class DashboardClientRecommendation(BaseModel):
    rank: int = Field(ge=1)
    client_id: uuid.UUID
    client_name: str
    urgency_score: int = Field(ge=0, le=100)
    reason: str
    recommended_action: str
    days_since_contact: int | None = Field(default=None, ge=0)
    conversation_count: int = Field(ge=0)
    href: str


class DashboardResponse(BaseModel):
    overview: DashboardOverview
    recent_clients: list[ClientListItem]
    recent_conversations: list[ConversationListItem]
    daily_brief: list[DashboardBriefItem]
    priorities: list[DashboardPriority]
    client_recommendations: list[DashboardClientRecommendation]
    alerts: list[str]
    followups: list[str]
