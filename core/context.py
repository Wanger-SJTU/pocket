"""Message / context management for the Agent Loop.

Keeps the running conversation (system prompt, user turns, assistant
replies, tool calls, tool results) and serializes it into whatever
format the LLM client expects.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal


Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class Message:
    """A single message in the conversation history.

    Attributes:
        role: Who produced the message.
        content: Text content (tool results may embed JSON).
        tool_call_id: For role == "tool", id of the tool invocation.
        name: For role == "tool", the tool name that produced this result.
    """

    role: Role
    content: str
    tool_call_id: str | None = None
    name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to an OpenAI-style message dict.

        Returns:
            Dict suitable for passing into an LLM chat request.
        """
        payload: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_call_id is not None:
            payload["tool_call_id"] = self.tool_call_id
        if self.name is not None:
            payload["name"] = self.name
        return payload


@dataclass
class Context:
    """Ordered conversation history with helpers for mutation.

    Attributes:
        messages: The message list, oldest first.
    """

    messages: list[Message] = field(default_factory=list)

    def set_system(self, prompt: str) -> None:
        """Set or replace the system prompt at position 0.

        Args:
            prompt: System-level instructions.
        """
        if self.messages and self.messages[0].role == "system":
            self.messages[0].content = prompt
        else:
            self.messages.insert(0, Message(role="system", content=prompt))

    def add(self, message: Message) -> None:
        """Append a message to the history.

        Args:
            message: Message to append.
        """
        self.messages.append(message)

    def add_user(self, content: str) -> None:
        """Append a user message.

        Args:
            content: Raw user input text.
        """
        self.add(Message(role="user", content=content))

    def add_tool_result(self, tool_name: str, tool_call_id: str, content: str) -> None:
        """Append a tool execution result.

        Args:
            tool_name: Name of the executed tool.
            tool_call_id: Identifier matching the assistant's tool call.
            content: Serialized tool output (truncate if huge).
        """
        # TODO: truncate oversized tool outputs before they blow up the prompt.
        self.add(Message(role="tool", content=content, tool_call_id=tool_call_id, name=tool_name))

    def render(self) -> list[dict[str, Any]]:
        """Render the full history for an LLM request.

        Returns:
            List of message dicts, oldest first.
        """
        return [m.to_dict() for m in self.messages]

    def to_json(self) -> str:
        """Dump the history to JSON (for logging / debugging).

        Returns:
            JSON string of the rendered message list.
        """
        return json.dumps(self.render(), ensure_ascii=False, indent=2)
