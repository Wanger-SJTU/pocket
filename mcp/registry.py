"""Bridge remote MCP tools into the framework's ToolRegistry.

Each remote tool becomes a local Tool whose spec name is prefixed with the
server name (e.g. "weather__current"), so multiple servers can coexist
without collisions.
"""

from __future__ import annotations

import logging
from typing import Any

from mcp.base import MCPClient, MCPToolInfo
from tools.base import Tool, ToolRegistry, ToolSpec

logger = logging.getLogger(__name__)


class MCPToolProxy(Tool):
    """Local proxy for one tool hosted on an MCP server."""

    def __init__(self, client: MCPClient, server_name: str, info: MCPToolInfo) -> None:
        """Bind the proxy to its client and remote tool description."""
        self.client = client
        self.server_name = server_name
        self.info = info

    @property
    def spec(self) -> ToolSpec:
        """Remote tool schema, namespaced by server name."""
        return ToolSpec(
            name=f"{self.server_name}__{self.info.name}",
            description=self.info.description or f"Tool {self.info.name} (MCP: {self.server_name})",
            parameters=self.info.input_schema or {"type": "object", "properties": {}},
        )

    def run(self, **kwargs: Any) -> str:
        """Forward the call over MCP and return the text result."""
        return self.client.call_tool(self.info.name, kwargs)


class MCPToolRegistry:
    """Connects MCP servers and bridges their tools into a ToolRegistry."""

    def __init__(self) -> None:
        """Create an empty bridge."""
        self._clients: list[MCPClient] = []

    def connect(self, client: MCPClient, server_name: str,
                registry: ToolRegistry) -> list[str]:
        """Connect one server and register its tools.

        Args:
            client: Connected (or connectable) MCP client.
            server_name: Prefix for the bridged tool names.
            registry: Target ToolRegistry.

        Returns:
            Names of successfully registered local proxies.
        """
        if not getattr(client, "_proc", None):
            client.connect()
        self._clients.append(client)
        registered: list[str] = []
        for info in client.list_tools():
            proxy = MCPToolProxy(client, server_name, info)
            try:
                registry.register(proxy)
                registered.append(proxy.spec.name)
            except (ValueError, TypeError) as exc:
                logger.warning("mcp tool %s not registered: %s", info.name, exc)
        return registered

    def close_all(self) -> None:
        """Close every connected MCP client."""
        for client in self._clients:
            try:
                client.close()
            except Exception as exc:  # noqa: BLE001
                logger.warning("mcp client close failed: %s", exc)
        self._clients.clear()
