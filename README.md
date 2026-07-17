# flask-chat-events

A lightweight Flask extension that standardizes common Socket.IO chat events on
top of [Flask-SocketIO](https://flask-socketio.readthedocs.io/).

> This is **not** a chat application and **not** a replacement for
> Flask-SocketIO. It is a tiny abstraction layer that gives you consistent
> event **names** and **payloads** so every project in your stack speaks the
> same wire protocol.

---

## Installation

```bash
pip install flask-chat-events
```

Requires **Python 3.11+**, **Flask** and **Flask-SocketIO**.

---

## Quick Start

```python
from flask import Flask
from flask_socketio import SocketIO
from flask_chat_events import ChatEvents

app = Flask(__name__)
socketio = SocketIO(app)

chat = ChatEvents(socketio)

chat.message(
    room="general",
    user_id=15,
    text="Hello",
)
```

The extension follows the standard Flask extension pattern, so the factory
style is supported too:

```python
chat = ChatEvents()
chat.init_app(socketio)
```

---

## API Reference

All emit methods return the exact dictionary payload that was sent, which is
handy for logging or for chaining (for example, feeding a message `id` into a
read receipt).

### `ChatEvents(socketio=None)` / `init_app(socketio)`

Bind the extension to a Flask-SocketIO instance.

### `message(room, user_id, text, *, id=None, created_at=None, **emit_kwargs)`

Emits **`chat:message`**.

```json
{
    "id": "...",
    "room": "...",
    "user_id": "...",
    "text": "...",
    "created_at": "..."
}
```

`id` defaults to a random UUID4 hex string and `created_at` defaults to the
current UTC time in ISO-8601 format when omitted.

### `typing_start(room, user_id, **emit_kwargs)`

Emits **`chat:typing:start`**.

### `typing_stop(room, user_id, **emit_kwargs)`

Emits **`chat:typing:stop`**.

```json
{
    "room": "...",
    "user_id": "..."
}
```

### `read(room, message_id, user_id, **emit_kwargs)`

Emits **`chat:read`**.

```json
{
    "room": "...",
    "message_id": "...",
    "user_id": "..."
}
```

### `presence(user_id, status="online", *, room=None, **emit_kwargs)`

Emits **`presence:update`**. Valid statuses are `online`, `offline`, `away`.
When `room` is omitted the event is broadcast to all connected clients.

```json
{
    "user_id": "...",
    "status": "online"
}
```

### Event names

| Constant             | Value                |
| -------------------- | -------------------- |
| `EVENT_MESSAGE`      | `chat:message`       |
| `EVENT_TYPING_START` | `chat:typing:start`  |
| `EVENT_TYPING_STOP`  | `chat:typing:stop`   |
| `EVENT_READ`         | `chat:read`          |
| `EVENT_PRESENCE`     | `presence:update`    |

### Exceptions

All inherit from `ChatEventError`:

- `MissingRoomError` — `room` is missing or empty
- `MissingUserIdError` — `user_id` is missing or empty
- `EmptyMessageError` — message `text` is missing or empty
- `InvalidStatusError` — presence `status` is not a valid value
- `NotInitializedError` — used before being bound to a SocketIO instance

---

## Example

A runnable demo lives in [`examples/app.py`](examples/app.py):

```bash
python examples/app.py
```

It demonstrates connect, join room, send message, typing indicator, read
receipt and presence update.

---

## License

Released under the [MIT License](LICENSE).

---

## Contributing

Contributions are welcome!

```bash
git clone https://github.com/example/flask-chat-events
cd flask-chat-events
pip install -e ".[dev]"
pytest
black flask_chat_events tests examples
```

Please keep the public API small, add type hints and docstrings, and cover new
behavior with tests.

---

## Future Roadmap

- Optional server-side event **handlers/decorators** (not just emit helpers)
- Pluggable **payload schemas** and validation backends (e.g. pydantic)
- Built-in **rate limiting** for typing/presence spam
- **Namespaced** rooms and multi-tenant helpers
- Reference **client SDKs** (JS/TS) that consume the standardized events
