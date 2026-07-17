"""flask-chat-events: standardized Socket.IO chat events for Flask-SocketIO."""

from __future__ import annotations

from .chat import (
    ChatEvents,
    ChatMessage,
    PresenceUpdate,
    ReadReceipt,
    TypingEvent,
)
from .constants import (
    EVENT_MESSAGE,
    EVENT_PRESENCE,
    EVENT_READ,
    EVENT_TYPING_START,
    EVENT_TYPING_STOP,
    STATUS_AWAY,
    STATUS_OFFLINE,
    STATUS_ONLINE,
    VALID_STATUSES,
)
from .exceptions import (
    ChatEventError,
    EmptyMessageError,
    InvalidStatusError,
    MissingRoomError,
    MissingUserIdError,
    NotInitializedError,
)

__version__ = "0.1.0"

__all__ = [
    "ChatEvents",
    "ChatMessage",
    "TypingEvent",
    "ReadReceipt",
    "PresenceUpdate",
    "EVENT_MESSAGE",
    "EVENT_TYPING_START",
    "EVENT_TYPING_STOP",
    "EVENT_READ",
    "EVENT_PRESENCE",
    "STATUS_ONLINE",
    "STATUS_OFFLINE",
    "STATUS_AWAY",
    "VALID_STATUSES",
    "ChatEventError",
    "MissingRoomError",
    "MissingUserIdError",
    "EmptyMessageError",
    "InvalidStatusError",
    "NotInitializedError",
    "__version__",
]
