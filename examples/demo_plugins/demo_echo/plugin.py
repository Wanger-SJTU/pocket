"""Demo plugin: registers an uppercase-echo tool and a review listener."""

from __future__ import annotations

from typing import Any

from plugins.base import Plugin, PluginContext
from tools.base import Tool, ToolSpec


class EchoTool(Tool):
    """Echoes its input in upper case."""

    @property
    def spec(self) -> ToolSpec:
        """Schema sent to the model."""
        return ToolSpec(
            name="echo_upper",
            description="Echo the given text in upper case.",
            parameters={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        )

    def run(self, **kwargs: Any) -> str:
        """Uppercase the text argument."""
        return str(kwargs.get("text", "")).upper()


class DemoPlugin(Plugin):
    """Registers echo_upper and logs every reviewed call."""

    def __init__(self) -> None:
        """Track whether setup ran."""
        self.started = False

    @property
    def name(self) -> str:
        """Unique plugin name."""
        return "demo-echo"

    def setup(self, context: PluginContext) -> None:
        """Register the tool and a review listener."""
        context.register_tool(EchoTool())
        context.on_review(self._log_review)
        self.started = True

    def _log_review(self, request: Any):
        """Return None (no opinion); just observe."""
        print(f"[plugin demo-echo] observed review request: {request.tool_name}")
        return None


def plugin_entry() -> Plugin:
    """Alternative factory style entry (unused by loader convention)."""
    return DemoPlugin()


PLUGIN = DemoPlugin
