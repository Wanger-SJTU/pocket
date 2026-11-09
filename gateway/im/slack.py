"""Slack gateway stub: Events API / Socket Mode -> IncomingMessage, reply via chat.postMessage.

TODO: real implementation notes
    Transport options:
        - Events API (webhook): subscribe to `message` / `app_mention` events;
          Slack POSTs an event JSON and requires the `url_verification`
          handshake (echo `challenge`).
        - Socket Mode: WebSocket connection via `slack-sdk`
          (`slack_sdk.socket_mode.aiohi`/`SocketModeClient`), no public URL.

    Event format highlights (app_mention in a channel):
        {
          "type": "event_callback",
          "event": {
            "type": "app_mention" | "message",
            "user": "U123",
            "channel": "C123" | "D123" (DM),
            "ts": "1700000000.000100",
            "thread_ts": "..." (present inside threads),
            "text": "<@UBOT> hello"
          }
        }
    Strip the `<@UBOT>` mention prefix; use `thread_ts` to reply in-thread;
    ignore bot-authored messages (event.bot_id) to avoid self-loops.

    Reply: POST https://slack.com/api/chat.postMessage
        {"channel": ..., "text": ...} with Authorization: Bearer <bot token>
    Files: files_upload_v2 (or files.getUploadURLExternal flow).

    Security: verify X-Slack-Signature (HMAC-SHA256 of timestamp+body with
    signing secret); dedupe by event_id.
"""

from __future__ import annotations

import logging
from typing import Any

from gateway.base import Attachment, Gateway

logger = logging.getLogger(__name__)


class SlackGateway(Gateway):
    """Slack gateway adapter (stub: transport left as TODO)."""

    def __init__(self, bot_token: str = "", signing_secret: str = "") -> None:
        """Store Slack app credentials.

        Args:
            bot_token: Bot User OAuth Token (xoxb-...).
            signing_secret: App signing secret for request signature verification.
        """
        super().__init__(name="slack")
        self.bot_token = bot_token
        self.signing_secret = signing_secret

    def parse_event(self, payload: dict[str, Any]) -> Any:  # noqa: ANN401
        """Normalize a Slack Events API payload into an IncomingMessage.

        Args:
            payload: Raw JSON body POSTed by Slack (url_verification or
                event_callback).

        Returns:
            A normalized `IncomingMessage`.

        Raises:
            NotImplementedError: Stub only.
        """
        # TODO: url_verification challenge; signature verification; ignore
        # event.bot_id; strip <@UBOT> mention; map channel -> chat_id,
        # user -> sender; thread_ts -> metadata; files -> Attachment via
        # files.info permalink_private download.
        raise NotImplementedError("SlackGateway.parse_event is a stub")

    def send(self, chat_id: str, text: str, attachments: list[Attachment] | None = None) -> None:
        """Send text (and optionally files) to a Slack channel/DM.

        Args:
            chat_id: Slack channel id (C.../D...).
            text: Text content to send.
            attachments: Optional files uploaded via files_upload_v2.

        Raises:
            NotImplementedError: Stub only.
        """
        # TODO: POST /api/chat.postMessage with Bearer token; attachments ->
        # files_upload_v2 with channels=[chat_id].
        raise NotImplementedError("SlackGateway.send is a stub")
