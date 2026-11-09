"""Tool base class and registry.

A Tool is a named, schema-described callable the LLM may invoke.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ToolSpec:
    """JSON-schema style description of a tool, sent to the LLM.

    Attributes:
        name: Unique tool name.
        description: Natural-language description for the model.
        parameters: JSON schema of the tool's arguments.
    """

    name: str
    description: str
    parameters: dict[str, Any]


class Tool(ABC):
    """Base class for all tools."""

    @property
    @abstractmethod
    def spec(self) -> ToolSpec:
        """Return the tool's schema/spec sent to the model."""
        raise NotImplementedError

    @abstractmethod
    def run(self, **kwargs: Any) -> str:
        """Execute the tool.

        Args:
            **kwargs: Validated arguments matching spec.parameters.

        Returns:
            String result to feed back into the model context.
        """
        raise NotImplementedError


class ToolRegistry:
    """Registry of tools available to the agent.

    Handles name lookup, spec listing, and execution with timeout.
    """

    def __init__(self) -> None:
        """Create an empty registry."""
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool.

        Args:
            tool: Tool instance; raises ValueError on duplicate name.
        """
        name = tool.spec.name
        if name in self._tools:
            raise ValueError(f"duplicate tool name: {name}")
        self._tools[name] = tool

    def register_fn(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        fn: Callable[..., str],
    ) -> None:
        """Convenience: wrap a plain function as a tool and register it.

        Args:
            name: Tool name.
            description: Description for the model.
            parameters: JSON schema of arguments.
            fn: Callable invoked with keyword arguments.
        """
        self.register(_FnTool(name, description, parameters, fn))

    def specs(self) -> list[dict[str, Any]]:
        """List all tool specs in provider-friendly dict form.

        Returns:
            List of {"type": "function", "function": {...}} dicts.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": t.spec.name,
                    "description": t.spec.description,
                    "parameters": t.spec.parameters,
                },
            }
            for t in self._tools.values()
        ]

    def execute(self, name: str, args: dict[str, Any], timeout: float = 30.0) -> str:
        """Execute a registered tool by name.

        Args:
            name: Tool name.
            args: Parsed arguments from the model.
            timeout: Max seconds to wait (TODO: enforce with a real timeout).

        Returns:
            Tool output string.

        Raises:
            KeyError: If the tool name is not registered.
            TypeError: If arguments do not match the tool signature.
        """
        if name not in self._tools:
            raise KeyError(name)
        # TODO: validate args against spec.parameters (jsonschema) before calling.
        # TODO: enforce `timeout` (e.g. concurrent.futures) instead of ignoring it.
        return self._tools[name].run(**args)


class _FnTool(Tool):
    """Adapter that exposes a plain function as a Tool."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        fn: Callable[..., str],
    ) -> None:
        """Store metadata and the callable.

        Args:
            name: Tool name.
            description: Description.
            parameters: JSON schema.
            fn: Implementation callable.
        """
        self._spec = ToolSpec(name=name, description=description, parameters=parameters)
        self._fn = fn

    @property
    def spec(self) -> ToolSpec:
        """Return the stored spec."""
        return self._spec

    def run(self, **kwargs: Any) -> str:
        """Invoke the wrapped function.

        Args:
            **kwargs: Tool arguments.

        Returns:
            The function's string result.
        """
        return self._fn(**kwargs)
