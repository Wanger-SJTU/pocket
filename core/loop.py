"""Core loop: perceive -> LLM (tool selection) -> execute tool -> feed back -> repeat."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from config import Config
from core.context import Context, Message
from core.review import ReviewDecision, ReviewGate, ReviewRequest
from llm.client import LLMClient, LLMResponse, ToolCall
from tools.base import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class LoopResult:
    """Final outcome of an agent loop run.

    Attributes:
        output: The assistant's final textual answer (empty if stopped early).
        steps: Number of loop iterations actually executed.
        stop_reason: Why the loop ended ("completed", "max_steps", "error").
    """

    output: str
    steps: int
    stop_reason: str


class AgentLoop:
    """Drives the classic agent loop until task completion or step limit.

    The loop:
        1. Feed the current context to the LLM.
        2. If the LLM returns tool calls -> execute them via the registry,
           append results to context, and continue.
        3. If the LLM returns plain content -> treat it as the final answer.
        4. Stop on completion, max_steps, or unrecoverable error.
    """

    def __init__(self, client: LLMClient, registry: ToolRegistry, config: Config,
                 review_gate: ReviewGate | None = None) -> None:
        """Wire up dependencies.

        Args:
            client: LLM client (stub or real).
            registry: Available tools the agent may call.
            config: Runtime configuration.
            review_gate: Optional pre-execution confirmation layer; None or
                a disabled gate means tools run without review.
        """
        self.client = client
        self.registry = registry
        self.config = config
        self.review_gate = review_gate

    def run(self, task: str) -> LoopResult:
        """Execute the agent loop for a user task.

        Args:
            task: The user's task description.

        Returns:
            LoopResult with the final answer and stop reason.
        """
        context = Context()
        context.set_system(self.config.system_prompt)
        context.add_user(task)

        for step in range(1, self.config.max_steps + 1):
            logger.info("step %d/%d", step, self.config.max_steps)
            try:
                response: LLMResponse = self.client.chat(
                    messages=context.render(),
                    tools=self.registry.specs(),
                    model=self.config.model_name,
                    temperature=self.config.temperature,
                )
            except Exception as exc:  # noqa: BLE001 - framework boundary
                logger.exception("LLM call failed")
                return LoopResult(output="", steps=step, stop_reason=f"error: {exc}")

            # Case 1: no tool calls -> the model's content is the final answer.
            if not response.tool_calls:
                return LoopResult(output=response.content, steps=step, stop_reason="completed")

            # Case 2: record assistant turn, execute tools, feed results back.
            context.add(Message(role="assistant", content=response.content))
            for call in response.tool_calls:
                result = self._execute(call)
                context.add_tool_result(call.name, call.id, result)

        return LoopResult(output="", steps=self.config.max_steps, stop_reason="max_steps")

    def _execute(self, call: ToolCall) -> str:
        """Execute one tool call and serialize its result.

        Args:
            call: Tool invocation requested by the LLM.

        Returns:
            String result to feed back into the context (error text on failure).
        """
        call_id = call.id or uuid.uuid4().hex
        try:
            args: dict[str, Any] = _parse_args(call.arguments)
            # ReviewGate: surface the plan before executing (sm.yw style).
            if self.review_gate is not None and self.review_gate.enabled:
                request = ReviewRequest(tool_name=call.name, arguments=args)
                decision: ReviewDecision = self.review_gate.check(request)
                if decision.action == "deny":
                    logger.info("review denied %s: %s", call.name, decision.feedback)
                    return f"review denied: {decision.feedback}. Revise your plan."
                if decision.action == "modify" and decision.arguments is not None:
                    args = decision.arguments
            output = self.registry.execute(call.name, args, timeout=self.config.tool_timeout_seconds)
            return output
        except KeyError as exc:
            return f"error: unknown tool {exc}"
        except Exception as exc:  # noqa: BLE001 - surface tool errors to the model
            logger.warning("tool %s failed: %s", call.name, exc)
            return f"error: {exc}"


def _parse_args(raw: str | None) -> dict[str, Any]:
    """Parse tool-call arguments from a JSON string.

    Args:
        raw: JSON object string (may be empty/None).

    Returns:
        Parsed dict, or empty dict for empty input.

    Raises:
        ValueError: If raw is non-empty but not valid JSON object.
    """
    # TODO: more tolerant parsing (repair malformed JSON the model emits).
    if not raw:
        return {}
    import json

    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("tool arguments must be a JSON object")
    return parsed
