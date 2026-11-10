"""Plugin base interfaces.

A Plugin is a code-level extension package with a lifecycle: it receives a
PluginContext at setup time and can register tools, hook into the loop's
review gate, or read config. Plugins are discovered from a plugins directory:
each subdirectory containing a plugin.py that exposes a PLUGIN class.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.review import ReviewDecision, ReviewRequest
    from tools.base import Tool


class PluginContext:
    """Capabilities handed to a plugin during setup.

    Wraps the registries a plugin is allowed to touch; anything not exposed
    here is off-limits by design.
    """

    def __init__(self, config: Any, tool_registry: Any, review_gate: Any = None) -> None:
        """Store references; typed loosely to avoid import cycles."""
        self.config = config
        self._tool_registry = tool_registry
        self._review_gate = review_gate

    def register_tool(self, tool: "Tool") -> None:
        """Register a tool into the agent's ToolRegistry.

        Args:
            tool: Tool instance to expose to the model.

        Raises:
            ValueError: Propagated from ToolRegistry on duplicate names.
        """
        self._tool_registry.register(tool)

    def register_reviewer(self, reviewer: Any) -> None:
        """Add a reviewer to the review gate (if one is wired up).

        Args:
            reviewer: Reviewer instance consulted before tool execution.
        """
        if self._review_gate is not None:
            self._review_gate.add_reviewer(reviewer)

    def on_review(self, callback: Any) -> None:
        """Subscribe a callback invoked for every ReviewRequest.

        Args:
            callback: Callable(request: ReviewRequest) -> ReviewDecision | None.
                Returning None means "no opinion".
        """
        if self._review_gate is not None:
            self._review_gate.add_listener(callback)


class Plugin(ABC):
    """Base class for all plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique plugin name."""
        raise NotImplementedError

    @abstractmethod
    def setup(self, context: PluginContext) -> None:
        """Wire the plugin into the agent. Called once at load time."""
        raise NotImplementedError

    def teardown(self) -> None:
        """Release resources. Called on shutdown (best-effort)."""
