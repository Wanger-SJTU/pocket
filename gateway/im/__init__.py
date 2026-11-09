"""IM adapter stubs: Feishu / Telegram / Slack (real transport left as TODO)."""

from gateway.im.feishu import FeishuGateway
from gateway.im.slack import SlackGateway
from gateway.im.telegram import TelegramGateway

__all__ = ["FeishuGateway", "SlackGateway", "TelegramGateway"]
