"""Global configuration for the Agent Loop framework.

Settings come from a JSON file with env vars taking precedence over file
values. Config file search order: explicit path > AGENT_LOOP_CONFIG env
var > ~/.agent-loop/config.json (user-level, primary) > config.json in
the repo root (project-level override). See config.example.json.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent
HOME_CONFIG_PATH = Path.home() / ".agent-loop" / "config.json"
REPO_CONFIG_PATH = REPO_ROOT / "config.json"


@dataclass
class ReviewConfig:
    """Pre-execution review layer configuration (off by default).

    Attributes:
        enabled: When True, tool calls pass through the ReviewGate first.
    """

    enabled: bool = False


@dataclass
class SandboxConfig:
    """Sandbox layer configuration (local backend by default).

    Attributes:
        backend: "local" (rlimit jail) / "docker" (container, degrades to
            local when unavailable) / "off" (no confinement; dev only).
        workspace_root: Directory tree commands are confined to; also the
            default mount for the docker backend.
        image: Container image for the docker backend.
        readonly: Mount the workspace read-only in docker.
        limits: Resource caps dict (cpu_seconds/memory_mb/file_size_mb/
            max_processes for local; memory_mb/cpus/max_processes for docker).
    """

    backend: str = "local"
    workspace_root: str = "workspace"
    image: str = "python:3.12-slim"
    readonly: bool = False
    limits: dict = field(default_factory=dict)

    def to_settings(self) -> dict:
        """Render this section as the settings dict factory.create_sandbox expects.

        Returns:
            Dict with backend/workspace_root/image/readonly/limits keys.
        """
        return {
            "backend": self.backend,
            "workspace_root": self.workspace_root,
            "image": self.image,
            "readonly": self.readonly,
            "limits": dict(self.limits),
        }


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
    context_token_limit: int = 0  # >0 enables auto-compact near this estimate
    review: ReviewConfig = field(default_factory=ReviewConfig)
    sandbox: SandboxConfig = field(default_factory=SandboxConfig)
    skills_dir: str = ""       # directory of skill subdirs; empty = disabled
    plugins_dir: str = ""      # directory of plugin subdirs; empty = disabled
    mcp_servers: list[dict[str, str]] = field(default_factory=list)
    extra: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_settings(cls, settings: dict | None) -> "Config":
        """Build a Config from parsed JSON settings, ignoring unknown keys.

        Args:
            settings: Raw settings dict (may be None/empty; see load_settings).

        Returns:
            Config with recognised fields applied over dataclass defaults.
        """
        settings = settings or {}
        config = cls()
        for key in ("max_steps", "model_name", "system_prompt", "temperature",
                    "tool_timeout_seconds", "context_token_limit",
                    "skills_dir", "plugins_dir"):
            if key in settings:
                setattr(config, key, settings[key])
        review = settings.get("review") or {}
        if "enabled" in review:
            config.review.enabled = bool(review["enabled"])
        sandbox = settings.get("sandbox") or {}
        for key in ("backend", "workspace_root", "image"):
            if key in sandbox:
                setattr(config.sandbox, key, str(sandbox[key]))
        if "readonly" in sandbox:
            config.sandbox.readonly = bool(sandbox["readonly"])
        if isinstance(sandbox.get("limits"), dict):
            config.sandbox.limits = dict(sandbox["limits"])
        return config


def load_settings(path: str | Path | None = None) -> tuple[dict, str]:
    """Load JSON settings from disk.

    Search order: explicit `path` arg > AGENT_LOOP_CONFIG env var >
    ~/.agent-loop/config.json > config.json next to this module. Missing
    default-location files are normal (empty settings); a malformed file
    logs a warning and is treated as missing so the agent still runs.

    Args:
        path: Optional explicit config file path.

    Returns:
        (settings dict, path actually loaded; "" when none was loaded).
    """
    if path:
        candidates: list[tuple[Path, bool]] = [(Path(path), True)]
    elif env_path := os.environ.get("AGENT_LOOP_CONFIG"):
        candidates = [(Path(env_path), True)]
    else:
        candidates = [(HOME_CONFIG_PATH, False), (REPO_CONFIG_PATH, False)]
    for config_path, explicit in candidates:
        if not config_path.is_file():
            if explicit:
                logger.warning("config file %s not found; using defaults", config_path)
            continue
        try:
            settings = json.loads(config_path.read_text(encoding="utf-8"))
            if not isinstance(settings, dict):
                raise ValueError("top-level JSON must be an object")
            return settings, str(config_path)
        except (ValueError, OSError) as exc:
            logger.warning("config file %s unreadable (%s); using defaults",
                           config_path, exc)
    return {}, ""
