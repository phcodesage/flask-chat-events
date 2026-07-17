"""flask-chat-events: standardized Socket.IO chat events for Flask-SocketIO."""

from __future__ import annotations

from .chat import (
    ChatEvents,
    ChatMessage,
    DeleteMessage,
    EditMessage,
    PresenceUpdate,
    ReadReceipt,
    TypingEvent,
)
from .constants import (
    EVENT_DELETE,
    EVENT_EDIT,
    EVENT_HISTORY,
    EVENT_MESSAGE,
    EVENT_PRESENCE,
    EVENT_READ,
    EVENT_TYPING_START,
    EVENT_TYPING_STOP,
    EVENT_USER_LIST,
    INBOUND_DELETE_MESSAGE,
    INBOUND_EDIT_MESSAGE,
    INBOUND_JOIN,
    INBOUND_LEAVE,
    INBOUND_MARK_READ,
    INBOUND_SEND_MESSAGE,
    INBOUND_TYPING,
    STATUS_AWAY,
    STATUS_OFFLINE,
    STATUS_ONLINE,
    VALID_STATUSES,
)
from .exceptions import (
    ChatEventError,
    EmptyMessageError,
    InvalidStatusError,
    MissingMessageIdError,
    MissingRoomError,
    MissingUserIdError,
    NotInitializedError,
)
from .handlers import InboundEvents, register_handlers
from .registry import PresenceRegistry
from .stores import InMemoryMessageStore, MessageStore

__version__ = "0.2.0"

__all__ = [
    # core
    "ChatEvents",
    "ChatMessage",
    "EditMessage",
    "DeleteMessage",
    "TypingEvent",
    "ReadReceipt",
    "PresenceUpdate",
    # storage & presence
    "MessageStore",
    "InMemoryMessageStore",
    "PresenceRegistry",
    # inbound wiring
    "register_handlers",
    "InboundEvents",
    # event-name constants
    "EVENT_MESSAGE",
    "EVENT_EDIT",
    "EVENT_DELETE",
    "EVENT_TYPING_START",
    "EVENT_TYPING_STOP",
    "EVENT_READ",
    "EVENT_PRESENCE",
    "EVENT_USER_LIST",
    "EVENT_HISTORY",
    # inbound event-name constants
    "INBOUND_JOIN",
    "INBOUND_LEAVE",
    "INBOUND_SEND_MESSAGE",
    "INBOUND_EDIT_MESSAGE",
    "INBOUND_DELETE_MESSAGE",
    "INBOUND_TYPING",
    "INBOUND_MARK_READ",
    # statuses
    "STATUS_ONLINE",
    "STATUS_OFFLINE",
    "STATUS_AWAY",
    "VALID_STATUSES",
    # exceptions
    "ChatEventError",
    "MissingRoomError",
    "MissingUserIdError",
    "MissingMessageIdError",
    "EmptyMessageError",
    "InvalidStatusError",
    "NotInitializedError",
    "__version__",
]
