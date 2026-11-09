"""Gateway base: normalized message types and the abstract Gateway interface."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Attachment:
    """A file/media attached to an IM message.

    Attributes:
        kind: Attachment type ("image", "file", "audio", "video", ...).
        url: Remote URL of the resource, if any.
        local_path: Local file path (e.g. after download), if any.
        filename: Original filename as reported by the IM platform.
        metadata: Platform-specific extra fields (mime type, size, file_key...).
    """

    kind: str = "file"
    url: str | None = None
    local_path: str | None = None
    filename: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IncomingMessage:
    """A normalized message received from an IM platform.

    Attributes:
        sender: Platform user id of the sender.
        chat_id: Conversation identifier (chat/group/user id, platform-specific).
        text: Plain text content (may be empty for attachment-only messages).
        attachments: Attached files/media.
        metadata: Platform-specific extras (message id, thread id, raw event...).
    """

    sender: str
    chat_id: str
    text: str = ""
    attachments: list[Attachment] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OutgoingMessage:
    """A normalized reply to be delivered back to an IM platform.

    Attributes:
        chat_id: Target conversation (should mirror the incoming chat_id).
        text: Reply text.
        attachments: Optional files/media to send.
        metadata: Platform-specific extras (reply_to message id, thread id...).
    """

    chat_id: str
    text: str
    attachments: list[Attachment] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class GatewayStatus(str, Enum):
    """Lifecycle state of a gateway."""

    STOPPED = "stopped"
    RUNNING = "running"
    ERROR = "error"


# Callback signature: called with each normalized incoming message.
MessageHandler = Callable[[IncomingMessage], None]


class Gateway(ABC):
    """Abstract base class for IM gateway adapters.

    Contract:
        - `start()` brings the transport up (webhook server / websocket / polling).
        - While running, received IM events are normalized into `IncomingMessage`
          and passed to the registered `on_message` handler (e.g. a shim that
          runs an `AgentLoop`).
        - The agent's reply is delivered back via `send()`.
        - `stop()` tears the transport down; the gateway must be restartable.
    """

    def __init__(self, name: str) -> None:
        """Initialize the gateway.

        Args:
            name: Adapter name, e.g. "feishu", "telegram", "echo".
        """
        self.name = name
        self.status: GatewayStatus = GatewayStatus.STOPPED
        self._handler: MessageHandler | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the gateway transport and mark it RUNNING.

        Subclasses should call `super().start()` after their transport is up.
        """
        logger.info("gateway %s starting", self.name)
        self.status = GatewayStatus.RUNNING

    def stop(self) -> None:
        """Stop the gateway transport and mark it STOPPED.

        Subclasses should call `super().stop()` after tearing down their
        transport. Idempotent: stopping a stopped gateway is a no-op.
        """
        logger.info("gateway %s stopped", self.name)
        self.status = GatewayStatus.STOPPED

    # ------------------------------------------------------------------
    # Inbound: IM -> Agent
    # ------------------------------------------------------------------

    def on_message(self, handler: MessageHandler) -> None:
        """Register the callback invoked for every normalized incoming message.

        Args:
            handler: Callable receiving an `IncomingMessage`; typically wraps
                an `AgentLoop.run(task=...)` call and calls `send()` with the
                result.
        """
        self._handler = handler

    def dispatch(self, message: IncomingMessage) -> None:
        """Hand a normalized incoming message to the registered handler.

        Args:
            message: The normalized message from the IM platform.

        Raises:
            RuntimeError: If no handler has been registered.
        """
        if self._handler is None:
            raise RuntimeError(
                f"gateway {self.name}: no on_message handler registered; "
                "call gateway.on_message(fn) before start()"
            )
        logger.info("gateway %s dispatching msg from chat=%s", self.name, message.chat_id)
        self._handler(message)

    # ------------------------------------------------------------------
    # Outbound: Agent -> IM
    # ------------------------------------------------------------------

    @abstractmethod
    def send(self, chat_id: str, text: str, attachments: list[Attachment] | None = None) -> None:
        """Send a reply back to the IM conversation.

        Args:
            chat_id: Target conversation id (as received in IncomingMessage).
            text: Reply text content.
            attachments: Optional files/media to attach.
        """
        raise NotImplementedError
