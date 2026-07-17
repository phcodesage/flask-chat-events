"""Batteries-included inbound Socket.IO handler wiring.

:func:`register_handlers` installs a complete, server-authoritative chat backend
on a :class:`~flask_chat_events.chat.ChatEvents` instance: it listens for the
client *intent* events (join, send_message, typing, …), authenticates the user
**server-side** (the client-supplied ``user_id`` is never trusted), keeps the
:class:`~flask_chat_events.registry.PresenceRegistry` up to date, persists
history to the bound store, and rebroadcasts the standardized events.

This is the half of a chat app that every consumer otherwise re-implements by
hand. With a store and registry bound, a working backend is one call::

    chat = ChatEvents(socketio, store=InMemoryMessageStore(), registry=PresenceRegistry())
    chat.register_handlers(authenticate=lambda: session.get("username"))
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from flask import request
from flask_socketio import join_room, leave_room

from .constants import (
    INBOUND_DELETE_MESSAGE,
    INBOUND_EDIT_MESSAGE,
    INBOUND_JOIN,
    INBOUND_LEAVE,
    INBOUND_MARK_READ,
    INBOUND_SEND_MESSAGE,
    INBOUND_TYPING,
    STATUS_OFFLINE,
    STATUS_ONLINE,
)
from .exceptions import NotInitializedError

__all__ = ["InboundEvents", "register_handlers"]

# () -> user_id | None. Returns the authenticated user for the current
# connection (typically from the Flask session), or None to reject/ignore.
Authenticator = Callable[[], Optional[str]]
# (user_id) -> dict of per-connection metadata stored in the registry.
UserMeta = Callable[[str], Dict[str, Any]]


@dataclass(frozen=True)
class InboundEvents:
    """Client -> server event names ``register_handlers`` listens on.

    Override any field to match a client that uses different names.
    """

    join: str = INBOUND_JOIN
    leave: str = INBOUND_LEAVE
    send_message: str = INBOUND_SEND_MESSAGE
    edit_message: str = INBOUND_EDIT_MESSAGE
    delete_message: str = INBOUND_DELETE_MESSAGE
    typing: str = INBOUND_TYPING
    mark_read: str = INBOUND_MARK_READ


def register_handlers(
    chat: Any,
    authenticate: Authenticator,
    *,
    events: Optional[InboundEvents] = None,
    default_room: str = "general",
    send_history_on_join: bool = True,
    user_meta: Optional[UserMeta] = None,
) -> None:
    """Install the standard inbound handlers on ``chat``'s SocketIO server.

    ``authenticate`` resolves the current user's id (e.g.
    ``lambda: session.get("username")``); a falsy return rejects the connection
    and ignores subsequent events. ``user_meta`` optionally supplies extra
    per-connection fields (avatar color, display name) surfaced in user-list
    broadcasts. A :class:`~flask_chat_events.registry.PresenceRegistry` must be
    bound; a store is optional but required for ``send_history_on_join``.
    """
    socketio = chat.socketio  # raises NotInitializedError if unbound
    registry = chat.registry
    if registry is None:
        raise NotInitializedError(
            "register_handlers requires a PresenceRegistry. Pass registry=... "
            "to ChatEvents."
        )
    events = events or InboundEvents()
    meta_for: UserMeta = user_meta or (lambda _uid: {})

    def _room(data: Any) -> str:
        room = (data or {}).get("room", default_room)
        return str(room) if room else default_room

    @socketio.on("connect")
    def _on_connect() -> Any:
        user_id = authenticate()
        if not user_id:
            return False  # reject unauthenticated connections
        registry.connect(request.sid, str(user_id), **meta_for(str(user_id)))
        chat.presence(user_id=str(user_id), status=STATUS_ONLINE)
        chat.broadcast_user_list()
        return None

    @socketio.on("disconnect")
    def _on_disconnect() -> None:
        info = registry.disconnect(request.sid)
        if info is None:
            return
        if info["was_last"]:
            chat.presence(user_id=info["user_id"], status=STATUS_OFFLINE)
        for room in info["rooms"]:
            chat.broadcast_user_list(room=room)
        chat.broadcast_user_list()

    @socketio.on(events.join)
    def _on_join(data: Dict[str, Any]) -> None:
        user_id = authenticate()
        if not user_id:
            return
        room = _room(data)
        join_room(room)
        registry.join(request.sid, room)
        if send_history_on_join and chat.store is not None:
            chat.send_history(room)
        chat.presence(user_id=str(user_id), status=STATUS_ONLINE, room=room)
        chat.broadcast_user_list(room=room)

    @socketio.on(events.leave)
    def _on_leave(data: Dict[str, Any]) -> None:
        user_id = authenticate()
        if not user_id:
            return
        room = _room(data)
        leave_room(room)
        registry.leave(request.sid, room)
        chat.broadcast_user_list(room=room)

    @socketio.on(events.send_message)
    def _on_send_message(data: Dict[str, Any]) -> None:
        user_id = authenticate()
        if not user_id:
            return
        text = str((data or {}).get("text", "")).strip()
        if not text:
            return
        chat.message(room=_room(data), user_id=str(user_id), text=text)

    @socketio.on(events.edit_message)
    def _on_edit_message(data: Dict[str, Any]) -> None:
        user_id = authenticate()
        if not user_id:
            return
        room = _room(data)
        message_id = (data or {}).get("message_id")
        text = str((data or {}).get("text", "")).strip()
        if not message_id or not text:
            return
        chat.edit(room=room, message_id=message_id, user_id=str(user_id), text=text)

    @socketio.on(events.delete_message)
    def _on_delete_message(data: Dict[str, Any]) -> None:
        user_id = authenticate()
        if not user_id:
            return
        message_id = (data or {}).get("message_id")
        if not message_id:
            return
        chat.delete(room=_room(data), message_id=message_id, user_id=str(user_id))

    @socketio.on(events.typing)
    def _on_typing(data: Dict[str, Any]) -> None:
        user_id = authenticate()
        if not user_id:
            return
        room = _room(data)
        is_typing = (data or {}).get("is_typing", True)
        if is_typing:
            chat.typing_start(room=room, user_id=str(user_id), include_self=False)
        else:
            chat.typing_stop(room=room, user_id=str(user_id), include_self=False)

    @socketio.on(events.mark_read)
    def _on_mark_read(data: Dict[str, Any]) -> None:
        user_id = authenticate()
        if not user_id:
            return
        message_id = (data or {}).get("message_id")
        if not message_id:
            return
        chat.read(room=_room(data), message_id=message_id, user_id=str(user_id))
