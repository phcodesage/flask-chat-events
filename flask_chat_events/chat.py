"""Core ChatEvents implementation.

This module provides a small abstraction layer on top of Flask-SocketIO that
standardizes chat-related event names and payloads. It is intentionally *not*
a chat application and *not* a replacement for Flask-SocketIO.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .constants import (
    EVENT_MESSAGE,
    EVENT_PRESENCE,
    EVENT_READ,
    EVENT_TYPING_START,
    EVENT_TYPING_STOP,
    STATUS_ONLINE,
    VALID_STATUSES,
)
from .exceptions import (
    EmptyMessageError,
    InvalidStatusError,
    MissingRoomError,
    MissingUserIdError,
    NotInitializedError,
)

__all__ = [
    "ChatEvents",
    "ChatMessage",
    "TypingEvent",
    "ReadReceipt",
    "PresenceUpdate",
]


def _utcnow_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _require_room(room: Any) -> str:
    """Validate and normalize a ``room`` value."""
    if room is None or (isinstance(room, str) and not room.strip()):
        raise MissingRoomError()
    return str(room)


def _require_user_id(user_id: Any) -> str:
    """Validate and normalize a ``user_id`` value."""
    if user_id is None or (isinstance(user_id, str) and not user_id.strip()):
        raise MissingUserIdError()
    return str(user_id)


@dataclass(frozen=True)
class ChatMessage:
    """A single chat message payload."""

    id: str
    room: str
    user_id: str
    text: str
    created_at: str


@dataclass(frozen=True)
class TypingEvent:
    """A typing-start / typing-stop payload."""

    room: str
    user_id: str


@dataclass(frozen=True)
class ReadReceipt:
    """A read-receipt payload."""

    room: str
    message_id: str
    user_id: str


@dataclass(frozen=True)
class PresenceUpdate:
    """A presence-update payload."""

    user_id: str
    status: str


class ChatEvents:
    """Standardized Socket.IO chat events on top of Flask-SocketIO.

    Supports both the direct and factory (``init_app``) initialization styles::

        chat = ChatEvents(socketio)

        # or

        chat = ChatEvents()
        chat.init_app(socketio)
    """

    def __init__(self, socketio: Optional[Any] = None) -> None:
        """Create a ChatEvents instance, optionally bound to ``socketio``."""
        self._socketio: Optional[Any] = None
        if socketio is not None:
            self.init_app(socketio)

    def init_app(self, socketio: Any) -> None:
        """Bind this extension to a Flask-SocketIO instance."""
        self._socketio = socketio

    @property
    def socketio(self) -> Any:
        """Return the bound SocketIO instance or raise if unbound."""
        if self._socketio is None:
            raise NotInitializedError()
        return self._socketio

    def message(
        self,
        room: Any,
        user_id: Any,
        text: str,
        *,
        id: Optional[str] = None,
        created_at: Optional[str] = None,
        **emit_kwargs: Any,
    ) -> Dict[str, Any]:
        """Emit a ``chat:message`` event and return the emitted payload.

        ``id`` defaults to a random UUID4 hex string and ``created_at`` defaults
        to the current UTC time in ISO-8601 format when omitted.
        """
        room = _require_room(room)
        user_id = _require_user_id(user_id)
        if text is None or not str(text).strip():
            raise EmptyMessageError()

        payload = ChatMessage(
            id=id or uuid.uuid4().hex,
            room=room,
            user_id=user_id,
            text=str(text),
            created_at=created_at or _utcnow_iso(),
        )
        return self._emit(EVENT_MESSAGE, payload, room=room, **emit_kwargs)

    def typing_start(
        self, room: Any, user_id: Any, **emit_kwargs: Any
    ) -> Dict[str, Any]:
        """Emit a ``chat:typing:start`` event and return the emitted payload."""
        payload = TypingEvent(
            room=_require_room(room), user_id=_require_user_id(user_id)
        )
        return self._emit(EVENT_TYPING_START, payload, room=payload.room, **emit_kwargs)

    def typing_stop(
        self, room: Any, user_id: Any, **emit_kwargs: Any
    ) -> Dict[str, Any]:
        """Emit a ``chat:typing:stop`` event and return the emitted payload."""
        payload = TypingEvent(
            room=_require_room(room), user_id=_require_user_id(user_id)
        )
        return self._emit(EVENT_TYPING_STOP, payload, room=payload.room, **emit_kwargs)

    def read(
        self, room: Any, message_id: Any, user_id: Any, **emit_kwargs: Any
    ) -> Dict[str, Any]:
        """Emit a ``chat:read`` event and return the emitted payload."""
        payload = ReadReceipt(
            room=_require_room(room),
            message_id=str(message_id),
            user_id=_require_user_id(user_id),
        )
        return self._emit(EVENT_READ, payload, room=payload.room, **emit_kwargs)

    def presence(
        self,
        user_id: Any,
        status: str = STATUS_ONLINE,
        *,
        room: Optional[Any] = None,
        **emit_kwargs: Any,
    ) -> Dict[str, Any]:
        """Emit a ``presence:update`` event and return the emitted payload.

        ``status`` must be one of the values in
        :data:`flask_chat_events.constants.VALID_STATUSES`. When ``room`` is
        omitted, the event is broadcast to all connected clients.
        """
        if status not in VALID_STATUSES:
            raise InvalidStatusError(status, VALID_STATUSES)
        payload = PresenceUpdate(user_id=_require_user_id(user_id), status=status)
        target_room = None if room is None else _require_room(room)
        return self._emit(EVENT_PRESENCE, payload, room=target_room, **emit_kwargs)

    def _emit(
        self,
        event: str,
        payload: Any,
        *,
        room: Optional[str] = None,
        **emit_kwargs: Any,
    ) -> Dict[str, Any]:
        """Serialize ``payload`` and forward it to ``socketio.emit()``."""
        data = asdict(payload)
        if room is not None:
            emit_kwargs.setdefault("room", room)
        self.socketio.emit(event, data, **emit_kwargs)
        return data
