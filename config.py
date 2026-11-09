"""Global configuration for the Agent Loop framework.

TODO:
    - Load from env vars / YAML file instead of hardcoding.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Config:
    """Runtime configuration for an agent loop run.

    Attributes:
        max_steps: Hard cap on LLM->tool iterations before forced stop.
        model_name: Identifier of the model the LLM client should target.
        system_prompt: System message prepended to every conversation.
        temperature: Sampling temperature passed through to the LLM client.
        tool_timeout_seconds: Per-tool execution timeout.
        extra: Free-form settings, reserved for future use.
    """

    max_steps: int = 10
    model_name: str = "stub-model"
    system_prompt: str = "You are a helpful agent. Use tools when needed."
    temperature: float = 0.2
    tool_timeout_seconds: float = 30.0
    extra: dict[str, str] = field(default_factory=dict)
