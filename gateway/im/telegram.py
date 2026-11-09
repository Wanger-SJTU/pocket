"""Telegram gateway stub: webhook or getUpdates polling -> IncomingMessage, send via Bot API.

TODO: real implementation notes
    Transport options:
        - Webhook: `setWebhook` to an HTTPS URL; Telegram POSTs an `Update` JSON.
        - Long polling: loop `getUpdates?timeout=50&offset=last_update_id+1`.

    Update format highlights (message of type text):
        {
          "update_id": 123,
          "message": {
            "message_id": 456,
            "from": {"id": 111, "username": "user"},
            "chat": {"id": 111 or -100222 (group)},
            "text": "hello",
            "photo": [...], "document": {"file_id": ..., "file_name": ...}
          }
        }
    For groups, gate on "bot" in message.entities to only react to /commands
    or mentions; keep chat.id for replies.

    Reply: POST https://api.telegram.org/bot<token>/sendMessage
        {"chat_id": ..., "text": ...}
    Files: sendDocument / sendPhoto with multipart file or file_id;
    downloads via getFile + https://api.telegram.org/file/bot<token>/<path>.

    Security: validate secret_token header set in setWebhook.
"""

from __future__ import annotations

import logging
from typing import Any

from gateway.base import Attachment, Gateway

logger = logging.getLogger(__name__)


class TelegramGateway(Gateway):
    """Telegram Bot API gateway adapter (stub: transport left as TODO)."""

    def __init__(self, bot_token: str = "", secret_token: str = "") -> None:
        """Store Telegram bot credentials.

        Args:
            bot_token: Bot token from @BotFather.
            secret_token: Optional X-Telegram-Bot-Api-Secret-Token for webhook auth.
        """
        super().__init__(name="telegram")
        self.bot_token = bot_token
        self.secret_token = secret_token

    def parse_update(self, payload: dict[str, Any]) -> Any:  # noqa: ANN401
        """Normalize a Telegram `Update` into an IncomingMessage.

        Args:
            payload: Raw JSON body of a webhook Update (or one getUpdates item).

        Returns:
            A normalized `IncomingMessage`.

        Raises:
            NotImplementedError: Stub only.
        """
        # TODO: pick message/edited_message/channel_post; map chat.id -> chat_id,
        # from.id -> sender; text or caption; photo/document -> Attachment
        # (resolve file_id via getFile). Ignore non-message updates.
        raise NotImplementedError("TelegramGateway.parse_update is a stub")

    def send(self, chat_id: str, text: str, attachments: list[Attachment] | None = None) -> None:
        """Send text (and optionally documents/photos) to a Telegram chat.

        Args:
            chat_id: Telegram chat id (positive for private, negative for groups).
            text: Text content to send.
            attachments: Optional media sent via sendDocument/sendPhoto.

        Raises:
            NotImplementedError: Stub only.
        """
        # TODO: POST /bot<token>/sendMessage; attachments -> multipart
        # sendDocument/sendPhoto with chat_id.
        raise NotImplementedError("TelegramGateway.send is a stub")
