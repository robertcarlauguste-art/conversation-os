from pydantic import BaseModel

from app.client.schemas import ClientListItem
from app.conversation.schemas import ConversationListItem


class DashboardOverview(BaseModel):
    clients: int
    conversations: int
    completed: int
    processing: int
    failed: int


class DashboardResponse(BaseModel):
    overview: DashboardOverview
    recent_clients: list[ClientListItem]
    recent_conversations: list[ConversationListItem]
    alerts: list[str]
    followups: list[str]