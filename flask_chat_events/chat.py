"""Core ChatEvents implementation.

This module provides a small abstraction layer on top of Flask-SocketIO that
standardizes chat-related event names and payloads. It is intentionally *not*
a chat application and *not* a replacement for Flask-SocketIO.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

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
    STATUS_ONLINE,
    VALID_STATUSES,
)
from .exceptions import (
    EmptyMessageError,
    InvalidStatusError,
    MissingMessageIdError,
    MissingRoomError,
    MissingUserIdError,
    NotInitializedError,
)
from .registry import PresenceRegistry
from .stores import MessageStore

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .handlers import InboundEvents

# A hook that transforms a message payload dict before it is emitted/stored.
MessageDecorator = Callable[[Dict[str, Any]], Dict[str, Any]]

__all__ = [
    "ChatEvents",
    "ChatMessage",
    "EditMessage",
    "DeleteMessage",
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


def _require_message_id(message_id: Any) -> str:
    """Validate and normalize a ``message_id`` value."""
    if message_id is None or (
        isinstance(message_id, str) and not message_id.strip()
    ):
        raise MissingMessageIdError()
    return str(message_id)


@dataclass(frozen=True)
class ChatMessage:
    """A single chat message payload."""

    id: str
    room: str
    user_id: str
    text: str
    created_at: str


@dataclass(frozen=True)
class EditMessage:
    """An edit to an existing chat message."""

    id: str
    room: str
    user_id: str
    text: str
    edited_at: str


@dataclass(frozen=True)
class DeleteMessage:
    """A deletion of an existing chat message."""

    id: str
    room: str
    user_id: str


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

    def __init__(
        self,
        socketio: Optional[Any] = None,
        *,
        store: Optional[MessageStore] = None,
        registry: Optional[PresenceRegistry] = None,
        message_decorator: Optional[MessageDecorator] = None,
    ) -> None:
        """Create a ChatEvents instance, optionally bound to ``socketio``.

        ``store`` enables automatic message-history persistence (see
        :meth:`history`). ``registry`` enables presence/room tracking and
        :meth:`broadcast_user_list`. ``message_decorator`` is applied to every
        message payload before it is emitted and stored — use it to attach
        derived fields such as an avatar color.
        """
        self._socketio: Optional[Any] = None
        self._store = store
        self._registry = registry
        self._message_decorator = message_decorator
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

    @property
    def store(self) -> Optional[MessageStore]:
        """The bound message-history store, if any."""
        return self._store

    @property
    def registry(self) -> Optional[PresenceRegistry]:
        """The bound presence registry, if any."""
        return self._registry

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

        message = ChatMessage(
            id=id or uuid.uuid4().hex,
            room=room,
            user_id=user_id,
            text=str(text),
            created_at=created_at or _utcnow_iso(),
        )
        data = asdict(message)
        if self._message_decorator is not None:
            data = self._message_decorator(data)
        self.socketio.emit(EVENT_MESSAGE, data, **self._room_kwargs(room, emit_kwargs))
        if self._store is not None:
            self._store.add(room, data)
        return data

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

    def edit(
        self,
        room: Any,
        message_id: Any,
        user_id: Any,
        text: str,
        *,
        edited_at: Optional[str] = None,
        **emit_kwargs: Any,
    ) -> Dict[str, Any]:
        """Emit a ``chat:edit`` event and return the emitted payload.

        When a store is bound, the stored message's ``text`` is updated too.
        ``edited_at`` defaults to the current UTC time in ISO-8601 format.
        """
        room = _require_room(room)
        user_id = _require_user_id(user_id)
        message_id = _require_message_id(message_id)
        if text is None or not str(text).strip():
            raise EmptyMessageError()

        payload = EditMessage(
            id=message_id,
            room=room,
            user_id=user_id,
            text=str(text),
            edited_at=edited_at or _utcnow_iso(),
        )
        data = self._emit(EVENT_EDIT, payload, room=room, **emit_kwargs)
        if self._store is not None:
            self._store.edit(room, message_id, data["text"], edited_at=data["edited_at"])
        return data

    def delete(
        self, room: Any, message_id: Any, user_id: Any, **emit_kwargs: Any
    ) -> Dict[str, Any]:
        """Emit a ``chat:delete`` event and return the emitted payload.

        When a store is bound, the stored message is removed too.
        """
        payload = DeleteMessage(
            id=_require_message_id(message_id),
            room=_require_room(room),
            user_id=_require_user_id(user_id),
        )
        data = self._emit(EVENT_DELETE, payload, room=payload.room, **emit_kwargs)
        if self._store is not None:
            self._store.delete(payload.room, payload.id)
        return data

    def history(self, room: Any, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return stored message history for ``room`` (oldest first).

        Requires a bound :class:`~flask_chat_events.stores.MessageStore`.
        """
        if self._store is None:
            raise NotInitializedError(
                "No message store is bound. Pass store=... to ChatEvents to "
                "enable history."
            )
        return self._store.history(_require_room(room), limit)

    def send_history(
        self, room: Any, *, limit: Optional[int] = None, **emit_kwargs: Any
    ) -> Dict[str, Any]:
        """Emit a ``chat:history`` event with a room's stored messages.

        Handy inside a ``join`` handler to prime a newly joined client. By
        default it is sent only to the requesting client (Socket.IO's implicit
        recipient); pass ``to=``/``room=`` to target others.
        """
        room = _require_room(room)
        data = {"room": room, "messages": self.history(room, limit)}
        self.socketio.emit(EVENT_HISTORY, data, **emit_kwargs)
        return data

    def broadcast_user_list(
        self, room: Optional[Any] = None, **emit_kwargs: Any
    ) -> Dict[str, Any]:
        """Emit a ``presence:list`` event with the current online users.

        With ``room`` set, lists users in that room and targets it; otherwise
        lists all online users and broadcasts. Requires a bound
        :class:`~flask_chat_events.registry.PresenceRegistry`.
        """
        if self._registry is None:
            raise NotInitializedError(
                "No presence registry is bound. Pass registry=... to ChatEvents "
                "to enable user-list broadcasts."
            )
        if room is None:
            # No room/to -> Flask-SocketIO broadcasts to every connected client.
            users = self._registry.online_users()
            data = {"room": None, "users": users}
        else:
            room = _require_room(room)
            users = self._registry.users_in(room)
            data = {"room": room, "users": users}
            emit_kwargs = self._room_kwargs(room, emit_kwargs)
        self.socketio.emit(EVENT_USER_LIST, data, **emit_kwargs)
        return data

    def register_handlers(
        self,
        authenticate: Callable[[], Optional[str]],
        *,
        events: "Optional[InboundEvents]" = None,
        default_room: str = "general",
        send_history_on_join: bool = True,
        user_meta: Optional[Callable[[str], Dict[str, Any]]] = None,
    ) -> None:
        """Install a full set of inbound Socket.IO handlers on the bound server.

        See :func:`flask_chat_events.handlers.register_handlers` for details.
        """
        from .handlers import register_handlers as _register

        _register(
            self,
            authenticate,
            events=events,
            default_room=default_room,
            send_history_on_join=send_history_on_join,
            user_meta=user_meta,
        )

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
        self.socketio.emit(event, data, **self._room_kwargs(room, emit_kwargs))
        return data

    @staticmethod
    def _room_kwargs(
        room: Optional[str], emit_kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Default the ``room`` emit kwarg without clobbering an explicit one."""
        if room is not None:
            emit_kwargs.setdefault("room", room)
        return emit_kwargs
