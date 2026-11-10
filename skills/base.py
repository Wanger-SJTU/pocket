"""Skill base interfaces.

A Skill is a loadable bundle of instructions (and optionally tools) that
extends the agent's capabilities without code changes. Skills are discovered
from a directory, each subdirectory holding a SKILL.md with YAML-ish front
matter (name/description) plus optional instruction body.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from tools.base import Tool


@dataclass
class SkillSpec:
    """Metadata describing one skill.

    Attributes:
        name: Unique skill name.
        description: Short description injected into system prompt summaries.
        version: Optional semver-ish version string.
        instructions: Instruction text (or path-relative marker) for the model.
        path: Filesystem root of the skill (empty for in-memory skills).
        extra: Any additional front-matter fields.
    """

    name: str
    description: str = ""
    version: str = "0.0.0"
    instructions: str = ""
    path: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


class Skill(ABC):
    """Base class for all skills."""

    @property
    @abstractmethod
    def spec(self) -> SkillSpec:
        """Return the skill's metadata."""
        raise NotImplementedError

    def tools(self) -> list[Tool]:
        """Tools this skill contributes to the registry (default: none).

        Returns:
            List of Tool instances; empty when the skill is instructions-only.
        """
        return []
