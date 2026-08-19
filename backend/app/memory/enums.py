import enum


class MemoryType(enum.StrEnum):
    """
    Only CONVERSATION_SUMMARY is produced this sprint. The vocabulary
    is deliberately open-ended (mirrors ConversationSource/Status from
    Sprint 1) so future sprints can add e.g. CLIENT_PREFERENCE or
    FOLLOW_UP without a schema change to this column.
    """

    CONVERSATION_SUMMARY = "CONVERSATION_SUMMARY"
