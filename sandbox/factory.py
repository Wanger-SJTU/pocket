"""Sandbox factory: pick a backend from config, with graceful degradation.

Selection rules (config sandbox.backend):
- "docker" -> DockerSandbox; raises/gets caught here -> degrade to local
- "local"  -> LocalSandbox
- "off"    -> NoneSandbox passthrough (development only: no confinement)

Callers (tools/examples.py, main.py) only ever see a Sandbox instance, so
swapping backends never touches tool code — same interface-only style as
memory/harness.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sandbox.base import Sandbox, SandboxUnavailable
from sandbox.docker_backend import DockerSandbox
from sandbox.local import LocalSandbox

logger = logging.getLogger(__name__)


class NoneSandbox(Sandbox):
    """Passthrough backend for explicit sandbox.backend="off" (dev only).

    Commands run as plain local subprocesses with NO confinement — the
    blocklist in tools/examples.py remains the only gate. Never use in
    anything that executes model-generated commands.
    """

    @property
    def name(self) -> str:
        """Backend identifier."""
        return "off"

    def run(
        self,
        cmd: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout: float = 30.0,
    ) -> "SandboxResult":
        """Run cmd as a bare subprocess (no jail). See Sandbox.run."""
        import subprocess
        try:
            completed = subprocess.run(
                ["/bin/sh", "-c", cmd], shell=False,
                capture_output=True, text=True, timeout=timeout, cwd=cwd,
            )
            from sandbox.base import SandboxResult
            return SandboxResult(
                stdout=completed.stdout or "", stderr=completed.stderr or "",
                exit_code=completed.returncode, backend=self.name,
            )
        except subprocess.TimeoutExpired:
            from sandbox.base import SandboxResult
            return SandboxResult(
                stderr=f"sandbox: command timed out after {timeout}s",
                exit_code=-1, timed_out=True, backend=self.name,
            )


def create_sandbox(settings: dict | None, workspace_root: str | Path) -> Sandbox:
    """Build the configured sandbox backend, degrading on unavailability.

    Args:
        settings: The config "sandbox" section (may be None for defaults).
        workspace_root: Default workspace both backends confine to.

    Returns:
        A Sandbox instance (never None); docker failures degrade to local
        with a warning, local/off always construct.

    Raises:
        Nothing — degradation is built in; check result.name to see what
        you actually got.
    """
    settings = settings or {}
    backend = str(settings.get("backend", "local")).lower()
    limits = settings.get("limits") or {}
    root = Path(settings.get("workspace_root") or workspace_root)
    if backend == "off":
        logger.warning("sandbox disabled (backend=off) — blocklist is the only gate")
        return NoneSandbox()
    if backend == "docker":
        try:
            return DockerSandbox(
                workspace_root=root, limits=limits,
                image=str(settings.get("image", "python:3.12-slim")),
                readonly=bool(settings.get("readonly", False)),
            )
        except SandboxUnavailable as exc:
            logger.warning("docker sandbox unavailable (%s); degrading to local", exc)
    return LocalSandbox(workspace_root=root, limits=limits)
