"""dispatch_task tool: lets the agent delegate subtasks to a harness."""

from __future__ import annotations

from typing import Any

from harness.base import HarnessRegistry, HarnessStatus
from tools.base import Tool, ToolSpec


class DispatchTaskTool(Tool):
    """Delegate a self-contained subtask to a registered harness.

    The LLM picks a harness by name and describes the subtask; the tool
    submits it and returns a serialized HarnessResult.
    """

    def __init__(self, harness_registry: HarnessRegistry) -> None:
        """Store the harness registry to dispatch through.

        Args:
            harness_registry: Registry containing available harnesses.
        """
        self._harnesses = harness_registry

    @property
    def spec(self) -> ToolSpec:
        """Return the tool schema (harness enum built from the registry)."""
        return ToolSpec(
            name="dispatch_task",
            description=(
                "Delegate a self-contained subtask to an external coding harness "
                "(e.g. claude_code, codex, openclaw, local_agent_loop). "
                "The subtask must include everything the child agent needs."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "harness": {
                        "type": "string",
                        "description": "Name of the harness to dispatch to.",
                        # TODO: keep enum in sync when harnesses register dynamically.
                        "enum": self._harnesses.names(),
                    },
                    "task": {
                        "type": "string",
                        "description": "Full, self-contained task description."
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional extra context (findings, file paths)."
                    },
                },
                "required": ["harness", "task"],
            },
        )

    def run(self, *, harness: str, task: str, context: str | None = None) -> str:
        """Submit the task to the named harness and serialize the result.

        Args:
            harness: Registered harness name.
            task: Subtask description.
            context: Optional extra context.

        Returns:
            Human/LLM-readable result summary string.
        """
        try:
            target = self._harnesses.get(harness)
        except KeyError:
            return f"error: unknown harness '{harness}'; available: {self._harnesses.names()}"
        try:
            result = target.submit(task, context)
        except Exception as exc:  # noqa: BLE001 - surface dispatch errors to the model
            return f"error: harness '{harness}' failed to accept task: {exc}"

        lines = [f"harness: {harness}", f"status: {result.status.value}"]
        if result.output:
            lines.append(f"output:\n{result.output}")
        if result.error:
            lines.append(f"error: {result.error}")
        if result.meta:
            lines.append(f"meta: {result.meta}")
        if result.status is HarnessStatus.FAILED:
            # TODO: consider automatic retry/fallback to another harness here.
            pass
        return "\n".join(lines)
