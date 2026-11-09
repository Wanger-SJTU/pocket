"""Stub adapters for external coding harnesses.

Each adapter shows the interface shape but does NOT actually invoke the
external CLI/API — real implementations are left as TODOs so the
framework stays offline-runnable.
"""

from __future__ import annotations

import logging

from harness.base import Harness, HarnessResult, HarnessStatus

logger = logging.getLogger(__name__)


class ClaudeCodeHarness(Harness):
    """Adapter for the Claude Code CLI (stub)."""

    @property
    def name(self) -> str:
        """Harness name used for dispatch lookup."""
        return "claude_code"

    def submit(self, task: str, context: str | None = None) -> HarnessResult:
        """Dispatch the task to Claude Code.

        Args:
            task: Task description.
            context: Optional extra context passed alongside the task.

        Returns:
            HarnessResult (currently always FAILED with a stub message).
        """
        # TODO: invoke `claude -p <task> --output-format json` (or the SDK),
        #   pass `context` via --append-system-prompt or an initial message,
        #   parse the JSON output into HarnessResult(output=..., meta={"session_id": ...}),
        #   map non-zero exit codes to HarnessStatus.FAILED.
        logger.info("ClaudeCodeHarness stub called for task: %.80s", task)
        return HarnessResult(
            status=HarnessStatus.FAILED,
            output="",
            error="claude_code adapter is a stub; real CLI invocation not implemented",
        )


class CodexHarness(Harness):
    """Adapter for the Codex CLI/API (stub)."""

    @property
    def name(self) -> str:
        """Harness name used for dispatch lookup."""
        return "codex"

    def submit(self, task: str, context: str | None = None) -> HarnessResult:
        """Dispatch the task to Codex.

        Args:
            task: Task description.
            context: Optional extra context.

        Returns:
            HarnessResult (currently always FAILED with a stub message).
        """
        # TODO: invoke `codex exec <task>` (headless mode) or the Responses API,
        #   set cwd/sandbox flags, capture stdout as HarnessResult.output,
        #   implement submit_async via Popen + poll on process liveness.
        logger.info("CodexHarness stub called for task: %.80s", task)
        return HarnessResult(
            status=HarnessStatus.FAILED,
            output="",
            error="codex adapter is a stub; real CLI invocation not implemented",
        )


class OpenClawHarness(Harness):
    """Adapter for OpenClaw agents (stub)."""

    @property
    def name(self) -> str:
        """Harness name used for dispatch lookup."""
        return "openclaw"

    def submit(self, task: str, context: str | None = None) -> HarnessResult:
        """Dispatch the task to an OpenClaw agent session.

        Args:
            task: Task description.
            context: Optional extra context.

        Returns:
            HarnessResult (currently always FAILED with a stub message).
        """
        # TODO: spawn `openclaw --message <task>` / use the gateway API to
        #   create a subagent session, await completion event, collect the
        #   final agent message into HarnessResult.output; cancel maps to
        #   session abort.
        logger.info("OpenClawHarness stub called for task: %.80s", task)
        return HarnessResult(
            status=HarnessStatus.FAILED,
            output="",
            error="openclaw adapter is a stub; real integration not implemented",
        )
