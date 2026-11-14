"""Example tools: read_file (root-guarded) and run_command (blocklist + sandbox).

Safety is layered: the command blocklist is the first gate (a cheap tripwire
for obviously-destructive strings), the Sandbox backend is the second wall
(confinement that holds even when the blocklist misses something). Tools
only depend on the Sandbox interface — swap backends at wiring time.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from sandbox.base import Sandbox
from tools.base import Tool, ToolSpec

# Commands that must never run, matched as substrings (lowercased).
_COMMAND_BLOCKLIST = [
    "rm -rf /", "rm -fr /", "mkfs", "dd if=", "> /dev/sd",
    "shutdown", "reboot", "poweroff", "halt",
    ":(){ :|:& };:", "fork()",
]


class ReadFileTool(Tool):
    """Read a text file and return its contents (confined to a root)."""

    def __init__(self, allowed_root: str | Path = ".") -> None:
        """Confine reads to a directory tree.

        Args:
            allowed_root: Workspace root; reads outside it are rejected.
                Absolute paths must resolve inside; relative paths resolve
                against this root.
        """
        self.allowed_root = Path(allowed_root).resolve()

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
            path: File path (absolute or relative to the allowed root).

        Returns:
            File text, or an error message.
        """
        try:
            target = Path(path)
            if not target.is_absolute():
                target = self.allowed_root / target
            target = target.resolve()
            if self.allowed_root != target and self.allowed_root not in target.parents:
                return (f"error: path {path!r} is outside the allowed root "
                        f"{str(self.allowed_root)!r}")
            with open(target, "r", encoding="utf-8") as handle:
                return handle.read()
        except OSError as exc:
            return f"error: {exc}"


class RunCommandTool(Tool):
    """Execute a shell command: blocklist first gate, sandbox second wall."""

    def __init__(self, sandbox: Sandbox) -> None:
        """Bind the execution backend.

        Args:
            sandbox: Any Sandbox implementation (local/docker/off); chosen
                once at wiring time, never inside the tool.
        """
        self.sandbox = sandbox

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
        """Screen the command against the blocklist, then run it in the sandbox.

        Args:
            command: Shell command string.
            cwd: Optional working directory (confined to the sandbox workspace).

        Returns:
            Combined stdout/stderr, truncated to a sane length.
        """
        # Gate 1: blocklist — a tripwire for obviously-destructive strings.
        lowered = command.lower()
        for pattern in _COMMAND_BLOCKLIST:
            if re.search(re.escape(pattern), lowered):
                return f"error: command rejected by blocklist (matched {pattern!r})"
        # Gate 2: sandbox — the wall (workspace jail + limits + kill).
        try:
            result = self.sandbox.run(command, cwd=cwd)
        except OSError as exc:
            return f"error: {exc}"
        if result.timed_out:
            return f"error: command timed out and was killed by the " \
                   f"sandbox ({result.backend})"
        output = result.combined()
        if result.exit_code != 0 and not output:
            output = f"(exit code {result.exit_code})"
        return output[:10_000] or "(no output)"


def default_registry(sandbox: Sandbox | None = None) -> "Any":
    """Build a registry preloaded with the example tools.

    Args:
        sandbox: Backend for command execution; None builds a local sandbox
            rooted at the repo's workspace/ directory (see config sandbox.*
            to pick docker/degradation instead).

    Returns:
        ToolRegistry containing ReadFileTool and RunCommandTool.
    """
    from tools.base import ToolRegistry

    if sandbox is None:
        from sandbox.local import LocalSandbox
        sandbox = LocalSandbox(workspace_root=Path("workspace"))
    registry = ToolRegistry()
    registry.register(ReadFileTool(allowed_root=Path("workspace")))
    registry.register(RunCommandTool(sandbox))
    return registry
