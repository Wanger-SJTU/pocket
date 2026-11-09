"""Wrap this framework's own AgentLoop as a Harness (agent dispatches agent)."""

from __future__ import annotations

import logging
from typing import Callable

from core.loop import AgentLoop, LoopResult
from harness.base import Harness, HarnessResult, HarnessStatus

logger = logging.getLogger(__name__)


class LocalAgentLoopHarness(Harness):
    """Expose an AgentLoop instance (or factory) as a dispatchable Harness.

    This demonstrates "agent scheduling agent": a parent AgentLoop can
    hand a subtask to a fresh child AgentLoop through the uniform
    Harness interface.
    """

    def __init__(
        self,
        loop_factory: Callable[[], AgentLoop] | None = None,
        shared_loop: AgentLoop | None = None,
    ) -> None:
        """Wire up the child loop source.

        Exactly one of loop_factory / shared_loop should be provided.

        Args:
            loop_factory: Builds a fresh child AgentLoop per task
                (isolated context; preferred for parallel subtasks).
            shared_loop: Reuse one existing AgentLoop instance
                (serialized dispatch; shares config/tools).
        """
        if (loop_factory is None) == (shared_loop is None):
            raise ValueError("provide exactly one of loop_factory or shared_loop")
        self._loop_factory = loop_factory
        self._shared_loop = shared_loop

    @property
    def name(self) -> str:
        """Harness name used for dispatch lookup."""
        return "local_agent_loop"

    def submit(self, task: str, context: str | None = None) -> HarnessResult:
        """Run the child AgentLoop on the task and wrap its LoopResult.

        Args:
            task: Subtask description (becomes the child's user message).
            context: Optional extra context prepended to the task text.

        Returns:
            HarnessResult mapping LoopResult.stop_reason to status.

        Raises:
            HarnessError: If no loop source was configured.
        """
        loop = self._resolve_loop()
        prompt = task if not context else f"{context}\n\n---\n\nTask: {task}"
        try:
            result: LoopResult = loop.run(prompt)
        except Exception as exc:  # noqa: BLE001 - framework boundary
            logger.exception("local AgentLoop harness failed")
            return HarnessResult(
                status=HarnessStatus.FAILED, output="", error=f"child loop error: {exc}"
            )

        if result.stop_reason == "completed":
            status = HarnessStatus.COMPLETED
            error = None
        else:
            status = HarnessStatus.FAILED
            error = f"child loop stopped early: {result.stop_reason}"
        return HarnessResult(
            status=status,
            output=result.output,
            error=error,
            meta={"steps": result.steps, "stop_reason": result.stop_reason},
        )

    def _resolve_loop(self) -> AgentLoop:
        """Return the child loop (fresh from factory, or the shared one).

        Returns:
            An AgentLoop instance.

        Raises:
            HarnessError: If neither factory nor shared loop is set.
        """
        if self._loop_factory is not None:
            return self._loop_factory()
        if self._shared_loop is not None:
            # TODO: guard against concurrent dispatch on a shared loop
            #   (add a lock or reject re-entrant submit).
            return self._shared_loop
        raise HarnessError("LocalAgentLoopHarness has no loop source configured")
