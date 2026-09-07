import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.client.schemas import ClientListItem
from app.conversation.schemas import ConversationListItem


class DashboardOverview(BaseModel):
    clients: int
    conversations: int
    completed: int
    processing: int
    failed: int
    queued: int = 0
    stale: int = 0


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
    open_action_count: int = Field(default=0, ge=0)
    href: str


class DashboardNextAction(BaseModel):
    id: uuid.UUID
    action_item_ids: list[uuid.UUID]
    source_count: int = Field(ge=1)
    task: str
    due: str | None = None
    owner: str | None = None
    client_id: uuid.UUID | None = None
    client_name: str | None = None
    conversation_id: uuid.UUID
    conversation_title: str | None = None
    href: str


class DashboardActivityItem(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID | None = None
    client_name: str | None = None
    action: Literal[
        "complete",
        "snooze",
        "record_contact",
        "complete_action_item",
    ]
    description: str
    occurred_at: datetime
    snoozed_until: datetime | None = None
    href: str


class FollowupActionRequest(BaseModel):
    action: Literal["complete", "snooze", "record_contact"]
    snooze_days: int | None = Field(default=None, ge=1, le=30)

    @model_validator(mode="after")
    def validate_snooze_days(self) -> "FollowupActionRequest":
        if self.action == "snooze" and self.snooze_days is None:
            raise ValueError("snooze_days is required when snoozing")
        if self.action != "snooze" and self.snooze_days is not None:
            raise ValueError("snooze_days is only valid when snoozing")
        return self


class FollowupActionResult(BaseModel):
    client_id: uuid.UUID
    action: Literal["complete", "snooze", "record_contact"]
    snoozed_until: datetime | None = None
    recorded_at: datetime


class DashboardResponse(BaseModel):
    overview: DashboardOverview
    recent_clients: list[ClientListItem]
    recent_conversations: list[ConversationListItem]
    daily_brief: list[DashboardBriefItem]
    priorities: list[DashboardPriority]
    client_recommendations: list[DashboardClientRecommendation]
    next_actions: list[DashboardNextAction]
    recent_activity: list[DashboardActivityItem]
    alerts: list[str]
    followups: list[str]
