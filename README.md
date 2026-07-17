# flask-chat-events

A lightweight Flask extension that standardizes common Socket.IO chat events on
top of [Flask-SocketIO](https://flask-socketio.readthedocs.io/).

> At its core this is a tiny abstraction layer that gives you consistent event
> **names** and **payloads** so every project in your stack speaks the same wire
> protocol. As of **0.2** it also ships optional *batteries* — a pluggable
> message-history store, presence/room tracking, and a one-call `register_handlers`
> that wires a complete, server-authoritative chat backend — so a working app can
> be a few lines instead of a page of `@socketio.on` handlers.

> **New in 0.2** (all additive — the 0.1 emit API is unchanged): `edit()` /
> `delete()` events, `InMemoryMessageStore` + `chat.history()`, `PresenceRegistry`,
> and `chat.register_handlers(...)`.

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

## Batteries-included backend (0.2)

If you want the whole inbound half of a chat app wired for you — receiving client
events, tracking presence, persisting history, and rebroadcasting — bind a store
and a registry, then call `register_handlers`:

```python
from flask import session
from flask_socketio import SocketIO
from flask_chat_events import ChatEvents, InMemoryMessageStore, PresenceRegistry

socketio = SocketIO(app)
chat = ChatEvents(
    socketio,
    store=InMemoryMessageStore(max_per_room=200),
    registry=PresenceRegistry(),
)

# Identity is resolved server-side — the client-supplied user_id is never trusted.
chat.register_handlers(authenticate=lambda: session.get("username"))
```

That single call installs handlers for `connect`, `disconnect`, `join`, `leave`,
`send_message`, `edit_message`, `delete_message`, `typing`, and `mark_read`,
each of which validates input, updates the registry/store, and emits the
standardized events below. New joiners are replayed room history via a
`chat:history` event, and presence changes fan out as `presence:list`.

Customize the client→server event names with `InboundEvents`, attach derived
fields (e.g. an avatar color) with `message_decorator=`, and surface per-user
metadata in presence lists with `user_meta=`.

See [`examples/registered_app.py`](examples/registered_app.py) for a complete,
tested app built this way.

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
current UTC time in ISO-8601 format when omitted. When a store is bound the
payload is persisted automatically; when a `message_decorator` is set it is
applied before the payload is emitted and stored.

### `edit(room, message_id, user_id, text, *, edited_at=None, **emit_kwargs)`

Emits **`chat:edit`**. `edited_at` defaults to the current UTC time. Updates the
stored message when a store is bound.

```json
{
    "id": "...",
    "room": "...",
    "user_id": "...",
    "text": "...",
    "edited_at": "..."
}
```

### `delete(room, message_id, user_id, **emit_kwargs)`

Emits **`chat:delete`**. Removes the stored message when a store is bound.

```json
{
    "id": "...",
    "room": "...",
    "user_id": "..."
}
```

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

### `history(room, limit=None)` / `send_history(room, *, limit=None, **emit_kwargs)`

`history` returns stored messages for a room (oldest first); `send_history`
emits them as a **`chat:history`** event (`{"room", "messages"}`). Both require a
bound store.

### `broadcast_user_list(room=None, **emit_kwargs)`

Emits **`presence:list`** (`{"room", "users"}`). With `room` set, lists users in
that room; otherwise lists everyone online and broadcasts. Requires a bound
registry.

### Storage & presence

- **`InMemoryMessageStore(max_per_room=200)`** — process-local history backend,
  capped per room. Implement the `MessageStore` interface (`add`, `history`,
  `get`, `edit`, `delete`, `clear`) to back history with Redis, a DB, etc.
- **`PresenceRegistry()`** — tracks `sid → user + metadata + rooms`. Query it
  with `online_users()`, `users_in(room)`, `is_online(user_id)`, `user_for(sid)`.

### `register_handlers(authenticate, *, events=None, default_room="general", send_history_on_join=True, user_meta=None)`

Installs the full inbound handler set (see
[Batteries-included backend](#batteries-included-backend-02)). Requires a bound
registry; a store is required for history replay.

### Event names

| Constant             | Value                |
| -------------------- | -------------------- |
| `EVENT_MESSAGE`      | `chat:message`       |
| `EVENT_EDIT`         | `chat:edit`          |
| `EVENT_DELETE`       | `chat:delete`        |
| `EVENT_TYPING_START` | `chat:typing:start`  |
| `EVENT_TYPING_STOP`  | `chat:typing:stop`   |
| `EVENT_READ`         | `chat:read`          |
| `EVENT_PRESENCE`     | `presence:update`    |
| `EVENT_USER_LIST`    | `presence:list`      |
| `EVENT_HISTORY`      | `chat:history`       |

Default inbound (client→server) names live in `INBOUND_*` constants and on the
`InboundEvents` dataclass.

### Exceptions

All inherit from `ChatEventError`:

- `MissingRoomError` — `room` is missing or empty
- `MissingUserIdError` — `user_id` is missing or empty
- `MissingMessageIdError` — `message_id` is missing or empty
- `EmptyMessageError` — message `text` is missing or empty
- `InvalidStatusError` — presence `status` is not a valid value
- `NotInitializedError` — used before being bound to a SocketIO instance (or a
  store/registry-dependent method called without one bound)

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

## Continuous Integration & Releases

CI lives in [`.github/workflows/workflow.yml`](.github/workflows/workflow.yml):

- **Every push / PR** runs the test suite on Python 3.11, 3.12 and 3.13.
- **A push to `main` whose tests pass** automatically:
  1. bumps the **patch** version in `pyproject.toml` and `flask_chat_events/__init__.py`,
  2. commits the bump (with `[skip ci]`) and pushes a `vX.Y.Z` tag,
  3. builds the sdist + wheel and **publishes to PyPI** via Trusted Publishing.

The bump commit is pushed with the built-in `GITHUB_TOKEN`, which does not
re-trigger workflows, and carries `[skip ci]` as a second guard — so there is no
release loop. Bump the **minor** or **major** version by hand (edit both files in
a normal commit) whenever a release warrants it; patch auto-bumps from there.

### One-time setup (required before the first publish)

The `publish` job uses **PyPI Trusted Publishing** (OIDC), so no API token is
stored in the repo — but PyPI must be told to trust this workflow:

1. On PyPI, go to **your account → Publishing → Add a new pending publisher**
   (or, for an existing project, **Project → Settings → Publishing**) and enter:
   - **PyPI Project Name:** `flask-chat-events`
   - **Owner:** `phcodesage`
   - **Repository:** `flask-chat-events`
   - **Workflow name:** `workflow.yml`
   - **Environment:** `release`
2. (Optional but recommended) In the GitHub repo, create an **Environment named
   `release`** (Settings → Environments) if you want approval gates or protection.

Until step 1 is done the test/bump/tag steps still work; only the final PyPI
upload will fail. To use an API token instead of OIDC, drop the `id-token`
permission and pass `password: ${{ secrets.PYPI_API_TOKEN }}` to the publish step.

---

## Future Roadmap

- ~~Optional server-side event **handlers/decorators** (not just emit helpers)~~ ✅ 0.2 (`register_handlers`)
- ~~Pluggable **message store**~~ ✅ 0.2 (`MessageStore`)
- ~~**Presence** / room membership tracking~~ ✅ 0.2 (`PresenceRegistry`)
- Pluggable **payload schemas** and validation backends (e.g. pydantic)
- Built-in **rate limiting** for typing/presence spam
- **Namespaced** rooms and multi-tenant helpers
- Reference **client SDKs** (JS/TS) that consume the standardized events
