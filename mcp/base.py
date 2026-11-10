"""MCP (Model Context Protocol) client interfaces.

MCP lets an agent call tools hosted in external processes/servers. This
package defines a transport-agnostic client interface plus a stdio (JSON-RPC
over subprocess) implementation and a bridge that maps remote MCP tools into
the framework's ToolRegistry.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MCPServerConfig:
    """Connection config for one MCP server.

    Exactly one of command (stdio transport) or url (HTTP transport) is set.

    Attributes:
        name: Logical server name; tool names are prefixed with it.
        command: Executable to spawn for stdio transport.
        args: Command arguments for stdio transport.
        env: Extra environment variables for the subprocess.
        url: Server URL for HTTP-based transports (not implemented here).
    """

    name: str
    command: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    url: str = ""


@dataclass
class MCPToolInfo:
    """Tool description returned by a server's tools/list."""

    name: str
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)


class MCPClient(ABC):
    """Transport-agnostic MCP client interface.

    Lifecycle: connect() -> list_tools()/call_tool() -> close().
    """

    @abstractmethod
    def connect(self) -> None:
        """Establish the connection (spawn process / open session)."""
        raise NotImplementedError

    @abstractmethod
    def list_tools(self) -> list[MCPToolInfo]:
        """Return the server's tool catalog."""
        raise NotImplementedError

    @abstractmethod
    def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Invoke a remote tool and return its text result.

        Args:
            name: Tool name as advertised by tools/list.
            arguments: Arguments matching the tool's input schema.

        Returns:
            Serialized text content of the tool result.
        """
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """Shut down the connection and release resources."""
        raise NotImplementedError
