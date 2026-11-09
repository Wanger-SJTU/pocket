"""Harness abstraction: dispatch subtasks to external coding agents.

A Harness is any external coding agent/CLI/API (Claude Code, Codex,
OpenClaw, or another AgentLoop instance) that can accept a task
description and produce a result.
"""

from harness.adapters import CodexHarness, ClaudeCodeHarness, OpenClawHarness  # noqa: F401
from harness.base import (  # noqa: F401
    Harness,
    HarnessError,
    HarnessRegistry,
    HarnessResult,
    HarnessStatus,
    create_default_registry,
)
