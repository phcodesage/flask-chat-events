"""A small but complete chat room built on flask-chat-events.

This is a *real* Flask-SocketIO application (not mocks). Clients emit intent
events (``join``, ``send_message``, ``typing``, ``stop_typing``, ``mark_read``)
and the server rebroadcasts them to the room using the standardized events from
flask-chat-events (``chat:message``, ``chat:typing:start`` …).

Run it::

    python examples/chat_app.py

then open http://127.0.0.1:5000/ in two browser tabs.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from flask import Flask, render_template_string
from flask_socketio import SocketIO, join_room, leave_room

from flask_chat_events import ChatEvents

INDEX_HTML = """
<!doctype html>
<meta charset="utf-8">
<title>flask-chat-events room</title>
<style>
  body { font: 15px system-ui; max-width: 640px; margin: 2rem auto; }
  #log { border: 1px solid #ccc; border-radius: 8px; height: 320px;
         overflow-y: auto; padding: .5rem 1rem; }
  .meta { color: #888; font-size: 12px; }
  form { display: flex; gap: .5rem; margin-top: .75rem; }
  input[type=text] { flex: 1; padding: .5rem; }
  #status { color: #2a7; min-height: 1.2em; }
</style>
<h2>Room: general</h2>
<div id="status"></div>
<div id="log"></div>
<form id="f">
  <input id="msg" type="text" autocomplete="off" placeholder="Type a message…">
  <button>Send</button>
</form>
<script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
<script>
  const uid = String(Math.floor(Math.random() * 1000));
  const room = "general";
  const socket = io();
  const log = (html, cls = "") =>
    (document.getElementById("log").insertAdjacentHTML("beforeend",
      `<div class="${cls}">${html}</div>`),
     document.getElementById("log").scrollTop = 1e9);

  socket.on("connect", () => socket.emit("join", { room, user_id: uid }));

  socket.on("chat:message", (d) =>
    log(`<b>user ${d.user_id}:</b> ${d.text} <span class="meta">${d.created_at}</span>`));
  socket.on("chat:typing:start", (d) =>
    document.getElementById("status").textContent = `user ${d.user_id} is typing…`);
  socket.on("chat:typing:stop", () =>
    document.getElementById("status").textContent = "");
  socket.on("chat:read", (d) =>
    log(`<span class="meta">user ${d.user_id} read message ${d.message_id}</span>`, "meta"));
  socket.on("presence:update", (d) =>
    log(`<span class="meta">user ${d.user_id} is ${d.status}</span>`, "meta"));

  const input = document.getElementById("msg");
  input.addEventListener("input", () => socket.emit("typing", { room, user_id: uid }));
  document.getElementById("f").addEventListener("submit", (e) => {
    e.preventDefault();
    if (!input.value.trim()) return;
    socket.emit("send_message", { room, user_id: uid, text: input.value });
    socket.emit("stop_typing", { room, user_id: uid });
    input.value = "";
  });
</script>
"""


def create_app() -> Tuple[Flask, SocketIO, ChatEvents]:
    """Build the Flask app, SocketIO server and ChatEvents extension.

    Returned as a tuple so tests can drive the same wiring the real server uses.
    """
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "demo-secret"
    socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")
    chat = ChatEvents(socketio)

    @app.route("/")
    def index() -> str:
        return render_template_string(INDEX_HTML)

    @socketio.on("join")
    def on_join(data: Dict[str, Any]) -> None:
        room, user_id = data["room"], data["user_id"]
        join_room(room)
        chat.presence(user_id=user_id, status="online", room=room)

    @socketio.on("leave")
    def on_leave(data: Dict[str, Any]) -> None:
        room, user_id = data["room"], data["user_id"]
        leave_room(room)
        chat.presence(user_id=user_id, status="offline", room=room)

    @socketio.on("send_message")
    def on_send_message(data: Dict[str, Any]) -> None:
        chat.message(room=data["room"], user_id=data["user_id"], text=data["text"])

    @socketio.on("typing")
    def on_typing(data: Dict[str, Any]) -> None:
        chat.typing_start(room=data["room"], user_id=data["user_id"])

    @socketio.on("stop_typing")
    def on_stop_typing(data: Dict[str, Any]) -> None:
        chat.typing_stop(room=data["room"], user_id=data["user_id"])

    @socketio.on("mark_read")
    def on_mark_read(data: Dict[str, Any]) -> None:
        chat.read(
            room=data["room"],
            message_id=data["message_id"],
            user_id=data["user_id"],
        )

    return app, socketio, chat


if __name__ == "__main__":
    app, socketio, _ = create_app()
    socketio.run(app, host="127.0.0.1", port=5000)
