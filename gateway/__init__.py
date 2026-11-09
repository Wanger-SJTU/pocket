"""Gateway abstraction: bridge external IM channels (Feishu, Telegram, Slack, ...) to AgentLoop.

Incoming IM messages are normalized into `IncomingMessage`, dispatched to a
registered callback (typically handed to an `AgentLoop`), and the agent reply
is sent back through `Gateway.send(chat_id, text)`.
"""

from gateway.base import (
    Attachment,
    Gateway,
    GatewayStatus,
    IncomingMessage,
    OutgoingMessage,
)
from gateway.router import GatewayRouter
from gateway.demo import EchoGateway, run_gateway_demo

__all__ = [
    "Attachment",
    "Gateway",
    "GatewayStatus",
    "IncomingMessage",
    "OutgoingMessage",
    "GatewayRouter",
    "EchoGateway",
    "run_gateway_demo",
]
