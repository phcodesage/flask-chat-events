"""The same chat backend as ``chat_app.py`` — but built with the 0.2 batteries.

Where ``chat_app.py`` hand-writes every ``@socketio.on`` handler, this wires the
entire inbound protocol (connect/disconnect/join/leave/send/edit/delete/typing/
read), message history, and presence tracking in a single
``chat.register_handlers(...)`` call.

Identity is server-authoritative: it comes from the connection handshake and is
remembered in the registry, so clients can never spoof another user's id.
"""

from __future__ import annotations

from typing import Optional, Tuple

from flask import Flask, request
from flask_socketio import SocketIO

from flask_chat_events import (
    ChatEvents,
    InMemoryMessageStore,
    PresenceRegistry,
)


def create_app() -> Tuple[Flask, SocketIO, ChatEvents]:
    """Build the app, wiring a complete chat backend in one call."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "demo-secret"
    socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")

    store = InMemoryMessageStore(max_per_room=200)
    registry = PresenceRegistry()
    chat = ChatEvents(socketio, store=store, registry=registry)

    def authenticate() -> Optional[str]:
        # After connect, identity is remembered per-connection in the registry;
        # on the initial handshake it comes from the ``user`` query param (a real
        # app would read the Flask session here instead).
        return registry.user_for(request.sid) or request.args.get("user")

    chat.register_handlers(authenticate=authenticate, default_room="general")

    return app, socketio, chat


if __name__ == "__main__":
    app, socketio, _ = create_app()
    socketio.run(app, host="127.0.0.1", port=5001)
