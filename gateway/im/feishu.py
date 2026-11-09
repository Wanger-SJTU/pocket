"""Feishu (Lark) gateway stub: event subscription -> IncomingMessage, send via IM API.

TODO: real implementation notes
    Transport options:
        - Event subscription (webhook): configure 事件订阅回调 URL; Feishu POSTs
          `type=event_callback` JSON. Must handle the `url_verification` challenge
          handshake first (echo back the `challenge` field).
        - Long connection (WebSocket): use open.feishu.cn SDK
          (`lark_oapi.ws.Client`), no public webhook URL needed.

    Event format highlights (im.message.receive_v1):
        {
          "schema": "2.0",
          "header": {"event_id": ..., "event_type": "im.message.receive_v1",
                     "token": <verification_token>, ...},
          "event": {
            "sender": {"sender_id": {"open_id": "ou_xxx", "user_id": "on_xxx"}},
            "message": {
              "chat_id": "oc_xxx",
              "message_id": "om_xxx",
              "message_type": "text",          # text / image / post / file ...
              "content": "{\"text\":\"hello\"}" # JSON string, parse per message_type
            }
          }
        }

    Reply: POST /open-apis/im/v1/messages?receive_id_type=chat_id with
        {"receive_id": chat_id, "msg_type": "text", "content": "{\"text\": ...}"}
    Optional: reply in-thread via /messages/{message_id}/reply.

    Security: verify `header.token` against the app's verification token /
    encrypt key; dedupe by `event_id` (Feishu retries on non-200).
"""

from __future__ import annotations

import logging
from typing import Any

from gateway.base import Attachment, Gateway

logger = logging.getLogger(__name__)


class FeishuGateway(Gateway):
    """Feishu gateway adapter (stub: raises NotImplementedError on transport)."""

    def __init__(
        self,
        app_id: str = "",
        app_secret: str = "",
        verification_token: str = "",
    ) -> None:
        """Store Feishu app credentials.

        Args:
            app_id: Feishu app id.
            app_secret: Feishu app secret (used to get tenant_access_token).
            verification_token: Event subscription verification token.
        """
        super().__init__(name="feishu")
        self.app_id = app_id
        self.app_secret = app_secret
        self.verification_token = verification_token

    def parse_event(self, payload: dict[str, Any]) -> Any:  # noqa: ANN401
        """Normalize a Feishu event payload into an IncomingMessage.

        Args:
            payload: Raw JSON body POSTed by Feishu event subscription.

        Returns:
            A normalized `IncomingMessage`.

        Raises:
            NotImplementedError: Stub only.
        """
        # TODO: url_verification challenge handling; token check; event_id dedupe;
        # parse event.message.content JSON by message_type (text/image/post/file);
        # map sender open_id / chat_id; download image/file resources into Attachment.
        raise NotImplementedError("FeishuGateway.parse_event is a stub")

    def send(self, chat_id: str, text: str, attachments: list[Attachment] | None = None) -> None:
        """Send text (and optionally files) to a Feishu chat.

        Args:
            chat_id: Feishu chat id (oc_...).
            text: Text content to send.
            attachments: Optional files; upload via /im/v1/files first, then
                send a file message.

        Raises:
            NotImplementedError: Stub only.
        """
        # TODO: get tenant_access_token (app_id+app_secret) -> POST
        # /open-apis/im/v1/messages?receive_id_type=chat_id; for attachments use
        # /open-apis/im/v1/files upload then msg_type=file.
        raise NotImplementedError("FeishuGateway.send is a stub")
