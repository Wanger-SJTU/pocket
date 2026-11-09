"""Example tool stubs: read_file and run_command.

These are intentionally minimal/stubbed — safe to extend with validation,
sandboxing, and real I/O.
"""

from __future__ import annotations

import subprocess
from typing import Any

from tools.base import Tool, ToolSpec


class ReadFileTool(Tool):
    """Read a text file and return its contents."""

    @property
    def spec(self) -> ToolSpec:
        """Return the tool schema."""
        return ToolSpec(
            name="read_file",
            description="Read the contents of a text file at the given path.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read."}
                },
                "required": ["path"],
            },
        )

    def run(self, *, path: str) -> str:
        """Read and return file contents.

        Args:
            path: File path.

        Returns:
            File text, or an error message.
        """
        # TODO: restrict to an allowed workspace root (path traversal guard).
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return handle.read()
        except OSError as exc:
            return f"error: {exc}"


class RunCommandTool(Tool):
    """Execute a shell command (stub-level safety)."""

    @property
    def spec(self) -> ToolSpec:
        """Return the tool schema."""
        return ToolSpec(
            name="run_command",
            description="Run a shell command and return combined stdout/stderr.",
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to run."},
                    "cwd": {"type": "string", "description": "Optional working directory."},
                },
                "required": ["command"],
            },
        )

    def run(self, *, command: str, cwd: str | None = None) -> str:
        """Run the command via subprocess.

        Args:
            command: Shell command string.
            cwd: Optional working directory.

        Returns:
            Combined stdout/stderr, truncated to a sane length.
        """
        # TODO: blocklist dangerous commands; run in a sandbox/container.
        try:
            completed = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=cwd,
            )
            output = (completed.stdout + completed.stderr).strip()
            return output[:10_000] or "(no output)"
        except subprocess.TimeoutExpired:
            return "error: command timed out after 30s"
        except OSError as exc:
            return f"error: {exc}"


def default_registry() -> "Any":
    """Build a registry preloaded with the example tools.

    Returns:
        ToolRegistry containing ReadFileTool and RunCommandTool.
    """
    from tools.base import ToolRegistry

    registry = ToolRegistry()
    registry.register(ReadFileTool())
    registry.register(RunCommandTool())
    return registry
