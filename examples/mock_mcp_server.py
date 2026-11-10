"""Mock MCP server for offline testing: newline-JSON JSON-RPC over stdio.

Exposes one tool `reverse` that reverses a string. Implements the minimal
MCP surface: initialize, notifications/initialized, tools/list, tools/call.
"""

from __future__ import annotations

import json
import sys


def main() -> None:
    """Serve JSON-RPC requests on stdin until EOF."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        message = json.loads(line)
        # Notifications carry no id; nothing to answer.
        if "id" not in message:
            continue
        method = message.get("method", "")
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "mock-mcp", "version": "0.1.0"},
            }
        elif method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": "reverse",
                        "description": "Reverse the given string.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"text": {"type": "string"}},
                            "required": ["text"],
                        },
                    }
                ]
            }
        elif method == "tools/call":
            text = message.get("params", {}).get("arguments", {}).get("text", "")
            result = {
                "content": [{"type": "text", "text": text[::-1]}],
                "isError": False,
            }
        else:
            result = {"content": [{"type": "text", "text": f"unknown method {method}"}],
                      "isError": True}
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": message["id"],
                                     "result": result}) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
