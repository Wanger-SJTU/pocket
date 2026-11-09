"""EchoGateway + gateway_demo: full IM in/out round-trip without any real IM platform."""

from __future__ import annotations

import logging

from gateway.base import Gateway, GatewayStatus, IncomingMessage
from gateway.router import GatewayRouter

logger = logging.getLogger(__name__)


class EchoGateway(Gateway):
    """Loopback gateway for demos/tests: `send()` just logs the outgoing reply.

    Feed it messages with `simulate_incoming()` to exercise the full flow:
    IncomingMessage -> dispatch -> handler -> send() -> OutgoingMessage (logged).
    """

    def __init__(self) -> None:
        """Create an idle echo gateway with an empty sent-log."""
        super().__init__(name="echo")
        self.sent: list[tuple[str, str]] = []

    def send(self, chat_id: str, text: str, attachments: list | None = None) -> None:
        """Record and log the reply instead of hitting a real IM API.

        Args:
            chat_id: Target conversation id.
            text: Reply text.
            attachments: Accepted but ignored (no transport).
        """
        self.sent.append((chat_id, text))
        logger.info("[echo] -> chat=%s text=%r", chat_id, text)

    def simulate_incoming(self, message: IncomingMessage) -> None:
        """Simulate an IM platform delivering a message to this gateway.

        Args:
            message: The normalized incoming message to dispatch.

        Raises:
            RuntimeError: If the gateway is not RUNNING (start() first).
        """
        if self.status is not GatewayStatus.RUNNING:
            raise RuntimeError("gateway not started; call start() before simulate_incoming()")
        self.dispatch(message)


def run_gateway_demo() -> None:
    """Run the end-to-end IM <-> Agent flow demo with EchoGateway.

    Wires: EchoGateway -> GatewayRouter(per-chat AgentLoop) -> AgentLoop.run ->
    gateway.send(chat_id, result.output). Uses the stub LLM client, fully offline.
    """
    from config import Config
    from core.loop import AgentLoop
    from llm.client import StubLLMClient
    from tools.examples import default_registry

    def make_loop() -> AgentLoop:
        """Build a fresh AgentLoop per chat (session isolation)."""
        return AgentLoop(client=StubLLMClient(), registry=default_registry(), config=Config(max_steps=3))

    router = GatewayRouter(loop_factory=make_loop)
    gateway = EchoGateway()

    def handle(message: IncomingMessage) -> None:
        """IM message handler: run the chat's AgentLoop and send the reply back."""
        loop = router.resolve(message.chat_id)
        result = loop.run(task=message.text)
        gateway.send(chat_id=message.chat_id, text=result.output or "(empty reply)")

    gateway.on_message(handle)
    gateway.start()

    gateway.simulate_incoming(IncomingMessage(sender="u1", chat_id="chat-A", text="Hello from IM!"))
    gateway.simulate_incoming(IncomingMessage(sender="u2", chat_id="chat-B", text="Second conversation."))
    gateway.simulate_incoming(IncomingMessage(sender="u1", chat_id="chat-A", text="Back to chat A."))

    gateway.stop()
    print(f"gateway status: {gateway.status.value}")
    print(f"replies sent: {len(gateway.sent)}")
    for chat_id, text in gateway.sent:
        print(f"  {chat_id}: {text[:60]}")
    print(f"router sessions: {sorted(router.sessions)} (one AgentLoop per chat)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    run_gateway_demo()
