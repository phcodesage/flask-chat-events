"""Minimal Flask + Flask-SocketIO app demonstrating flask-chat-events.

Run with::

    python examples/app.py

Then open http://127.0.0.1:5000/ in two browser tabs and watch the server
log as the standardized chat events are emitted.
"""

from __future__ import annotations

from flask import Flask, render_template_string
from flask_socketio import SocketIO, join_room

from flask_chat_events import ChatEvents

app = Flask(__name__)
app.config["SECRET_KEY"] = "demo-secret"
socketio = SocketIO(app, cors_allowed_origins="*")

# Bind the extension. ChatEvents(socketio) or init_app() both work.
chat = ChatEvents(socketio)

INDEX_HTML = """
<!doctype html>
<title>flask-chat-events demo</title>
<h1>flask-chat-events demo</h1>
<p>Open your browser console to see standardized events.</p>
<script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
<script>
  const socket = io();
  socket.on("connect", () => socket.emit("join", {room: "general", user_id: "42"}));
  for (const ev of [
    "chat:message", "chat:typing:start", "chat:typing:stop",
    "chat:read", "presence:update",
  ]) {
    socket.on(ev, (data) => console.log(ev, data));
  }
</script>
"""


@app.route("/")
def index() -> str:
    """Serve a tiny page that logs incoming chat events."""
    return render_template_string(INDEX_HTML)


@socketio.on("connect")
def on_connect() -> None:
    """Broadcast that a user came online when a client connects."""
    chat.presence(user_id="42", status="online")


@socketio.on("join")
def on_join(data: dict) -> None:
    """Join a room, then demonstrate every standardized event."""
    room = data.get("room", "general")
    user_id = data.get("user_id", "42")
    join_room(room)

    chat.presence(user_id=user_id, status="online", room=room)
    chat.typing_start(room=room, user_id=user_id)
    result = chat.message(room=room, user_id=user_id, text="Hello, world!")
    chat.typing_stop(room=room, user_id=user_id)
    chat.read(room=room, message_id=result["id"], user_id=user_id)


@socketio.on("disconnect")
def on_disconnect() -> None:
    """Broadcast that a user went offline when a client disconnects."""
    chat.presence(user_id="42", status="offline")


if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=5000)
