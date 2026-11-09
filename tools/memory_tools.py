"""memory_write / memory_search tools: expose a Memory backend to the agent.

Build these with `build_memory_tools(memory)` and register the returned
tools into the existing ToolRegistry (see tools/base.py).
"""

from __future__ import annotations

from typing import Any

from memory.base import Memory
from tools.base import Tool, ToolSpec


class MemoryWriteTool(Tool):
    """Write a new memory into the backend."""

    def __init__(self, memory: Memory) -> None:
        """Bind the tool to a memory backend.

        Args:
            memory: Any Memory implementation.
        """
        self._memory = memory

    @property
    def spec(self) -> ToolSpec:
        """Return the tool schema."""
        return ToolSpec(
            name="memory_write",
            description="Store a piece of information in long-term memory for later recall.",
            parameters={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The information to remember."},
                },
                "required": ["content"],
            },
        )

    def run(self, *, content: str) -> str:
        """Store the content and report the assigned id.

        Args:
            content: Text to remember.

        Returns:
            Confirmation string with the new memory id.
        """
        memory_id = self._memory.write(content)
        return f"stored memory id={memory_id}"


class MemorySearchTool(Tool):
    """Search the memory backend by keyword/relevance."""

    def __init__(self, memory: Memory) -> None:
        """Bind the tool to a memory backend.

        Args:
            memory: Any Memory implementation.
        """
        self._memory = memory

    @property
    def spec(self) -> ToolSpec:
        """Return the tool schema."""
        return ToolSpec(
            name="memory_search",
            description="Search long-term memory and return the most relevant entries.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to look for."},
                    "top_k": {"type": "integer", "description": "Max results (default 5)."},
                },
                "required": ["query"],
            },
        )

    def run(self, *, query: str, top_k: int = 5) -> str:
        """Search and format hits for the model.

        Args:
            query: Free-text query.
            top_k: Max hits.

        Returns:
            Formatted hit list (id, score, content), or "(no matches)".
        """
        hits = self._memory.search(query, top_k=top_k)
        if not hits:
            return "(no matches)"
        lines = [
            f"id={hit.record.id} score={hit.score:.2f} :: {hit.record.content}"
            for hit in hits
        ]
        return "\n".join(lines)


def build_memory_tools(memory: Memory) -> list[Tool]:
    """Construct the standard memory tool set for a backend.

    Args:
        memory: Any Memory implementation.

    Returns:
        [MemoryWriteTool, MemorySearchTool] ready for ToolRegistry.register().
    """
    return [MemoryWriteTool(memory), MemorySearchTool(memory)]
