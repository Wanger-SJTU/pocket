"""Simple router: chat_id -> AgentLoop instance/session mapping for multi-conversation isolation."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from core.loop import AgentLoop

logger = logging.getLogger(__name__)

# Factory that builds a fresh, fully-wired AgentLoop (client + tools + config).
LoopFactory = Callable[[], AgentLoop]


@dataclass
class Session:
    """One conversation session bound to a chat_id.

    Attributes:
        chat_id: IM conversation id this session serves.
        loop: The AgentLoop instance handling tasks from this chat.
    """

    chat_id: str
    loop: AgentLoop


@dataclass
class GatewayRouter:
    """Maps chat_id to a dedicated AgentLoop session.

    Default policy: one loop per chat (lazy creation via `loop_factory`),
    giving natural multi-conversation isolation. A shared single loop can be
    injected instead when cross-chat state sharing is desired.
    """

    loop_factory: LoopFactory
    sessions: dict[str, Session] = field(default_factory=dict)

    def resolve(self, chat_id: str) -> AgentLoop:
        """Return the AgentLoop bound to chat_id, creating one lazily.

        Args:
            chat_id: IM conversation id from an IncomingMessage.

        Returns:
            The AgentLoop instance for this conversation.
        """
        session = self.sessions.get(chat_id)
        if session is None:
            logger.info("router: creating new session for chat=%s", chat_id)
            session = Session(chat_id=chat_id, loop=self.loop_factory())
            self.sessions[chat_id] = session
        return session.loop

    def close(self, chat_id: str) -> None:
        """Drop the session bound to chat_id (next message gets a fresh loop).

        Args:
            chat_id: IM conversation id to forget.
        """
        self.sessions.pop(chat_id, None)
