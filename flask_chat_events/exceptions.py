"""Custom exceptions raised by flask-chat-events."""

from __future__ import annotations


class ChatEventError(Exception):
    """Base class for all flask-chat-events errors."""


class MissingRoomError(ChatEventError):
    """Raised when a required ``room`` argument is missing or empty."""

    def __init__(self, message: str = "A non-empty 'room' is required.") -> None:
        super().__init__(message)


class MissingUserIdError(ChatEventError):
    """Raised when a required ``user_id`` argument is missing or empty."""

    def __init__(self, message: str = "A non-empty 'user_id' is required.") -> None:
        super().__init__(message)


class EmptyMessageError(ChatEventError):
    """Raised when a message ``text`` is missing or empty."""

    def __init__(self, message: str = "Message 'text' must not be empty.") -> None:
        super().__init__(message)


class InvalidStatusError(ChatEventError):
    """Raised when a presence ``status`` is not one of the allowed values."""

    def __init__(self, status: object, valid: object) -> None:
        super().__init__(
            f"Invalid status {status!r}. Valid statuses are: "
            f"{', '.join(sorted(map(str, valid)))}."
        )


class MissingMessageIdError(ChatEventError):
    """Raised when a required ``message_id`` argument is missing or empty."""

    def __init__(self, message: str = "A non-empty 'message_id' is required.") -> None:
        super().__init__(message)


class NotInitializedError(ChatEventError):
    """Raised when ChatEvents is used before being bound to a SocketIO instance."""

    def __init__(
        self,
        message: str = (
            "ChatEvents is not bound to a SocketIO instance. "
            "Pass one to the constructor or call init_app()."
        ),
    ) -> None:
        super().__init__(message)
