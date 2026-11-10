"""Skill discovery and management.

SkillManager loads skills from a directory of subdirectories, each containing
a SKILL.md file with a minimal front matter block:

    ---
    name: my-skill
    description: what this skill does
    ---

    instruction body for the model ...

Loading a broken skill logs a warning and is skipped; one bad skill never
breaks the agent.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from skills.base import Skill, SkillSpec
from tools.base import Tool, ToolRegistry

logger = logging.getLogger(__name__)

_FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def parse_skill_md(text: str) -> tuple[dict[str, str], str]:
    """Split SKILL.md into (front-matter dict, body).

    Args:
        text: Raw SKILL.md contents.

    Returns:
        Tuple of simple key/value metadata (name/description/...) and the
        markdown body (instructions).
    """
    match = _FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip().strip("'\"")
    return meta, text[match.end():]


class FileSkill(Skill):
    """A skill loaded from a SKILL.md on disk."""

    def __init__(self, spec: SkillSpec) -> None:
        """Wrap already-parsed metadata + instructions."""
        self._spec = spec

    @property
    def spec(self) -> SkillSpec:
        """Return the parsed skill metadata."""
        return self._spec


class SkillManager:
    """Discovers and manages skills; injects them into prompt and registry."""

    def __init__(self) -> None:
        """Create an empty manager."""
        self._skills: dict[str, Skill] = {}

    def discover(self, skills_dir: str | Path) -> list[SkillSpec]:
        """Scan skills_dir: each subdir with SKILL.md becomes a skill.

        Args:
            skills_dir: Root directory containing one subdir per skill.

        Returns:
            List of successfully loaded skill specs.
        """
        root = Path(skills_dir)
        if not root.is_dir():
            logger.warning("skills_dir %s does not exist; skipping discovery", root)
            return []
        loaded: list[SkillSpec] = []
        for child in sorted(root.iterdir()):
            skill_md = child / "SKILL.md"
            if not skill_md.is_file():
                continue
            try:
                meta, body = parse_skill_md(skill_md.read_text(encoding="utf-8"))
                name = meta.get("name") or child.name
                skill = FileSkill(
                    SkillSpec(
                        name=name,
                        description=meta.get("description", ""),
                        version=meta.get("version", "0.0.0"),
                        instructions=body.strip(),
                        path=str(child),
                        extra={k: v for k, v in meta.items()
                               if k not in ("name", "description", "version")},
                    )
                )
                self.register(skill)
                loaded.append(skill.spec)
            except Exception as exc:  # noqa: BLE001 - one bad skill must not kill startup
                logger.warning("failed to load skill at %s: %s", child, exc)
        return loaded

    def register(self, skill: Skill) -> None:
        """Register a skill programmatically.

        Args:
            skill: The skill instance.

        Raises:
            ValueError: On duplicate skill name.
        """
        name = skill.spec.name
        if name in self._skills:
            raise ValueError(f"duplicate skill name: {name}")
        self._skills[name] = skill

    def skills(self) -> list[Skill]:
        """Return all registered skills."""
        return list(self._skills.values())

    def inject_instructions(self, system_prompt: str) -> str:
        """Append all skill instructions to a system prompt.

        Args:
            system_prompt: Base system prompt.

        Returns:
            Prompt with a "Skills" section appended (unchanged if no skills).
        """
        if not self._skills:
            return system_prompt
        parts = [system_prompt.rstrip(), "", "# Skills"]
        for skill in self._skills.values():
            spec = skill.spec
            parts.append(f"## {spec.name}: {spec.description}")
            if spec.instructions:
                parts.append(spec.instructions)
        return "\n".join(parts)

    def register_tools(self, registry: ToolRegistry) -> list[str]:
        """Register all skill-provided tools into a ToolRegistry.

        Args:
            registry: Target tool registry.

        Returns:
            Names of tools that were registered.
        """
        registered: list[str] = []
        for skill in self._skills.values():
            for tool in skill.tools():
                try:
                    registry.register(tool)
                    registered.append(tool.spec.name)
                except (ValueError, TypeError) as exc:
                    logger.warning("skill %s tool %s not registered: %s",
                                   skill.spec.name, tool.spec.name, exc)
        return registered
