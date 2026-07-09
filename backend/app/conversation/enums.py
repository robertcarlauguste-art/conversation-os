"""
Enums for the Conversation entity.

Split into their own module (rather than inlined in models.py) since
both `models.py` (DB column type) and `schemas.py` (API type) need
the same vocabulary, and neither should import from the other.
"""

import enum


class ConversationStatus(enum.StrEnum):
    UPLOADED = "UPLOADED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ConversationSource(enum.StrEnum):
    UPLOAD = "UPLOAD"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    IMPORT = "IMPORT"
