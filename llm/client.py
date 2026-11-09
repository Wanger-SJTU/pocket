"""Abstract LLM client interface + stub/mock implementation.

The real provider adapter (OpenAI / Anthropic / local) is left as a TODO;
the stub is fully functional for testing the loop offline.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    """A tool invocation requested by the model.

    Attributes:
        id: Unique identifier for this call (used to match tool results).
        name: Tool name to execute.
        arguments: JSON string of arguments.
    """

    id: str
    name: str
    arguments: str


@dataclass
class LLMResponse:
    """A normalized model response.

    Attributes:
        content: Textual reply (may be empty when only tools are requested).
        tool_calls: Tool invocations, empty list for a plain answer.
        raw: Provider-specific raw payload for debugging.
    """

    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


class LLMClient(ABC):
    """Provider-agnostic chat client interface."""

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str,
        temperature: float,
    ) -> LLMResponse:
        """Send a chat completion request.

        Args:
            messages: Rendered conversation history.
            tools: Tool specs (JSON-schema style) offered to the model.
            model: Model identifier.
            temperature: Sampling temperature.

        Returns:
            Normalized LLMResponse.
        """
        raise NotImplementedError


class StubLLMClient(LLMClient):
    """Deterministic mock client for offline testing.

    Plays back a scripted sequence of responses, then emits a final answer.
    """

    def __init__(self, script: list[LLMResponse] | None = None) -> None:
        """Create a stub client.

        Args:
            script: Optional scripted responses; defaults to one tool call
                (read_file) followed by a completion.
        """
        self._script = script or [
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCall(id="call-1", name="read_file", arguments='{"path": "README.md"}')
                ],
            ),
            LLMResponse(content="Done: file read successfully, task complete."),
        ]
        self._cursor = 0

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str,
        temperature: float,
    ) -> LLMResponse:
        """Return the next scripted response.

        Args:
            messages: Ignored by the stub.
            tools: Ignored by the stub.
            model: Ignored by the stub.
            temperature: Ignored by the stub.

        Returns:
            Next scripted LLMResponse, or a terminal completion when the
            script is exhausted.
        """
        if self._cursor < len(self._script):
            response = self._script[self._cursor]
            self._cursor += 1
            return response
        return LLMResponse(content="(stub exhausted) task complete.")


# TODO: RealLLMClient — implement against a real provider SDK.
# class RealLLMClient(LLMClient):
#     def chat(self, messages, tools, model, temperature) -> LLMResponse:
#         ...  # map tools to provider format, call API, normalize response
