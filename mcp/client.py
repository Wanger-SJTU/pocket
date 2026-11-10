"""MCP stdio transport: JSON-RPC 2.0 over a subprocess' stdin/stdout.

Implements the standard MCP handshake (initialize) and the tools/list and
tools/call methods. Messages are newline-delimited JSON, matching the common
stdio convention used by reference MCP servers.

TODO: untested against a real third-party MCP server; the bundled mock in
examples/mock_mcp_server.py exercises the protocol offline.
"""

from __future__ import annotations

import itertools
import json
import logging
import subprocess
from typing import Any

from mcp.base import MCPClient, MCPToolInfo, MCPServerConfig

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "2024-11-05"
CLIENT_INFO = {"name": "agent-loop", "version": "0.1.0"}


class StdioMCPClient(MCPClient):
    """Talks to an MCP server spawned as a subprocess."""

    def __init__(self, config: MCPServerConfig, timeout: float = 30.0) -> None:
        """Store config; connect() actually spawns the process.

        Args:
            config: Server config with command/args/env set.
            timeout: Per-request timeout in seconds.
        """
        self.config = config
        self.timeout = timeout
        self._proc: subprocess.Popen[str] | None = None
        self._request_ids = itertools.count(1)

    def connect(self) -> None:
        """Spawn the server process and run the MCP initialize handshake."""
        if self._proc is not None:
            return
        self._proc = subprocess.Popen(
            [self.config.command, *self.config.args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env={**dict(__import__("os").environ), **self.config.env},
            text=True,
            bufsize=1,
        )
        result = self._rpc("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": CLIENT_INFO,
        })
        logger.info("mcp %s initialized: %s", self.config.name, result.get("serverInfo", {}))
        self._notify("notifications/initialized", {})

    def list_tools(self) -> list[MCPToolInfo]:
        """Fetch the server's tool catalog via tools/list."""
        result = self._rpc("tools/list", {})
        return [
            MCPToolInfo(
                name=item.get("name", ""),
                description=item.get("description", ""),
                input_schema=item.get("inputSchema", {}) or {},
            )
            for item in result.get("tools", [])
        ]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Invoke a tool via tools/call and flatten its text content.

        Args:
            name: Remote tool name.
            arguments: JSON object of arguments.

        Returns:
            Concatenated text blocks of the tool result.

        Raises:
            RuntimeError: When the server reports the call as an error.
        """
        result = self._rpc("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            content = result.get("content", [])
            text = content[0].get("text", "") if content else "unknown MCP error"
            raise RuntimeError(text)
        parts = [block.get("text", "") for block in result.get("content", [])
                 if block.get("type") == "text"]
        return "\n".join(parts)

    def close(self) -> None:
        """Terminate the server process if running."""
        if self._proc is not None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None

    # -- JSON-RPC plumbing -------------------------------------------------

    def _rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Send one request and wait for the matching response.

        Raises:
            RuntimeError: On transport failure or JSON-RPC error response.
        """
        request = {"jsonrpc": "2.0", "id": next(self._request_ids),
                   "method": method, "params": params}
        assert self._proc is not None and self._proc.stdin and self._proc.stdout
        try:
            self._proc.stdin.write(json.dumps(request) + "\n")
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise RuntimeError(f"mcp {self.config.name} transport broken: {exc}") from exc
        while True:
            line = self._proc.stdout.readline()
            if not line:
                raise RuntimeError(f"mcp {self.config.name} closed the connection")
            message = json.loads(line)
            if message.get("id") != request["id"]:
                continue  # skip notifications/other responses
            if "error" in message:
                err = message["error"]
                raise RuntimeError(f"mcp error {err.get('code')}: {err.get('message')}")
            return message.get("result", {})

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        """Send a notification (no id, no response expected)."""
        assert self._proc is not None and self._proc.stdin
        notification = {"jsonrpc": "2.0", "method": method, "params": params}
        self._proc.stdin.write(json.dumps(notification) + "\n")
        self._proc.stdin.flush()
