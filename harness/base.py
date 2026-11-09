"""Harness base class, result types, and registry.

The Harness abstraction lets AgentLoop dispatch subtasks to external
coding harnesses (CLIs, APIs, or nested AgentLoop instances) through
one uniform interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HarnessStatus(str, Enum):
    """Lifecycle status of a dispatched task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class HarnessResult:
    """Outcome of a task dispatched to a harness.

    Attributes:
        status: Terminal (or current) status of the task.
        output: The harness's textual output (final answer / summary).
        error: Error message if status == FAILED, else None.
        meta: Harness-specific extra info (exit code, session id, ...).
    """

    status: HarnessStatus
    output: str = ""
    error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


class HarnessError(RuntimeError):
    """Raised when a harness cannot accept or execute a task."""


class Harness(ABC):
    """Abstract base class for external coding harnesses.

    Subclasses implement `submit` (and optionally async/poll/cancel).
    The interface is intentionally minimal: one task string in, one
    HarnessResult out.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique harness name used for dispatch lookup."""
        raise NotImplementedError

    @abstractmethod
    def submit(self, task: str, context: str | None = None) -> HarnessResult:
        """Dispatch a task to the harness and wait for its result.

        Args:
            task: Self-contained task description for the harness.
            context: Optional extra context (files, prior findings, ...).

        Returns:
            HarnessResult with status/output/error.

        Raises:
            HarnessError: If the harness cannot accept the task.
        """
        raise NotImplementedError

    # -- Optional async capabilities (framework stubs) -------------------

    def submit_async(self, task: str, context: str | None = None) -> str:
        """Dispatch a task without waiting; return a job id.

        Args:
            task: Task description.
            context: Optional extra context.

        Returns:
            Job id usable with `poll` / `cancel`.

        Raises:
            NotImplementedError: Until a subclass implements it.
        """
        # TODO: implement per-harness background dispatch (subprocess.Popen,
        # API job id, ...) and track jobs in a dict[str, HarnessJob].
        raise NotImplementedError(f"{type(self).__name__} does not support submit_async yet")

    def poll(self, job_id: str) -> HarnessResult:
        """Poll the status of an async job.

        Args:
            job_id: Id returned by `submit_async`.

        Returns:
            Current HarnessResult snapshot (status may be RUNNING/PENDING).

        Raises:
            NotImplementedError: Until a subclass implements it.
        """
        # TODO: return non-blocking status snapshot for the given job.
        raise NotImplementedError(f"{type(self).__name__} does not support poll yet")

    def cancel(self, job_id: str) -> bool:
        """Cancel a running/pending job.

        Args:
            job_id: Id returned by `submit_async`.

        Returns:
            True if cancellation was accepted, False otherwise.

        Raises:
            NotImplementedError: Until a subclass implements it.
        """
        # TODO: implement (kill process group / API cancel call).
        raise NotImplementedError(f"{type(self).__name__} does not support cancel yet")


class HarnessRegistry:
    """Name-keyed registry of available harnesses.

    Mirrors ToolRegistry: the dispatch tool resolves a harness by name.
    """

    def __init__(self) -> None:
        """Create an empty registry."""
        self._harnesses: dict[str, Harness] = {}

    def register(self, harness: Harness) -> None:
        """Register a harness.

        Args:
            harness: Harness instance; raises ValueError on duplicate name.
        """
        if harness.name in self._harnesses:
            raise ValueError(f"duplicate harness name: {harness.name}")
        self._harnesses[harness.name] = harness

    def get(self, name: str) -> Harness:
        """Look up a harness by name.

        Args:
            name: Registered harness name.

        Returns:
            The Harness instance.

        Raises:
            KeyError: If the name is not registered.
        """
        if name not in self._harnesses:
            raise KeyError(name)
        return self._harnesses[name]

    def names(self) -> list[str]:
        """List registered harness names.

        Returns:
            Sorted list of harness names.
        """
        return sorted(self._harnesses)


def create_default_registry() -> HarnessRegistry:
    """Build a registry preloaded with the stub external-harness adapters.

    Returns:
        HarnessRegistry containing the ClaudeCode/Codex/OpenClaw stubs.
        LocalAgentLoopHarness must be registered by the caller since it
        needs a live AgentLoop instance.
    """
    from harness.adapters import ClaudeCodeHarness, CodexHarness, OpenClawHarness

    registry = HarnessRegistry()
    registry.register(ClaudeCodeHarness())
    registry.register(CodexHarness())
    registry.register(OpenClawHarness())
    return registry
