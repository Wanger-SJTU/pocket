"""DockerSandbox: run commands inside an ephemeral `docker run --rm` container.

Strongest wall in this framework: filesystem is the mounted workspace only,
network is off, memory/CPU/PIDs are capped, and a timeout kill removes the
whole container. Uses the docker CLI via subprocess — no third-party deps.

If the docker CLI or daemon is unavailable, `SandboxUnavailable` is raised at
construction so the factory can degrade to LocalSandbox (or "off").
"""

from __future__ import annotations

import itertools
import logging
import os
import shutil
import subprocess
from pathlib import Path

from sandbox.base import Sandbox, SandboxResult, SandboxUnavailable

logger = logging.getLogger(__name__)


class DockerSandbox(Sandbox):
    """Containerized backend via the docker CLI (stdlib subprocess only)."""

    def __init__(
        self,
        workspace_root: str | Path,
        image: str = "python:3.12-slim",
        limits: dict | None = None,
        readonly: bool = False,
    ) -> None:
        """Check docker availability and bind the workspace mount.

        Args:
            workspace_root: Host directory mounted at /workspace in the
                container (read-write by default, `readonly` to lock down).
            image: Container image; pulled lazily by docker on first run.
            limits: Optional overrides: memory_mb, cpus, max_processes.
            readonly: Mount the workspace read-only when True.

        Raises:
            SandboxUnavailable: docker CLI missing or daemon unreachable.
        """
        if shutil.which("docker") is None:
            raise SandboxUnavailable("docker CLI not found on PATH")
        try:
            probe = subprocess.run(
                ["docker", "info", "--format", "{{.ServerVersion}}"],
                capture_output=True, text=True, timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SandboxUnavailable(f"docker probe failed: {exc}") from exc
        if probe.returncode != 0:
            raise SandboxUnavailable(
                f"docker daemon unreachable: {probe.stderr.strip()[:200]}"
            )
        self.workspace_root = Path(workspace_root).resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.image = image
        self.readonly = readonly
        self.limits = {**DEFAULT_LIMITS, **(limits or {})}
        self._counter = itertools.count()

    @property
    def name(self) -> str:
        """Backend identifier."""
        return "docker"

    def _docker_argv(self, cmd: str, timeout: float) -> list[str]:
        """Assemble the `docker run` argv for one execution.

        Args:
            cmd: Shell command to run inside the container.
            timeout: Wall-clock cap (used to size the docker-side budget).

        Returns:
            Argv list ready for subprocess.run.
        """
        mount_mode = "ro" if self.readonly else "rw"
        run_name = f"agent-loop-sb-{os.getpid()}-{next(self._counter)}"
        argv = [
            "docker", "run", "--rm", "--name", run_name,
            "--network", "none",                     # no egress, no SSRF
            "--memory", f"{self.limits['memory_mb']}m",
            "--memory-swap", f"{self.limits['memory_mb']}m",  # no swap escape
            "--cpus", str(self.limits["cpus"]),
            "--pids-limit", str(self.limits["max_processes"]),
            "--volume", f"{self.workspace_root}:/workspace:{mount_mode}",
            "--workdir", "/workspace",
            "--user", "nobody",                      # never root in the container
            self.image,
            "/bin/sh", "-c", cmd,
        ]
        return argv

    def run(
        self,
        cmd: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout: float = 30.0,
    ) -> SandboxResult:
        """Run `cmd` inside a throwaway container.

        Args:
            cmd: Shell command string (runs via /bin/sh in the container).
            cwd: Must be inside workspace_root; mapped onto /workspace.
            env: Extra env vars passed as `docker run -e` (client-side only;
                docker never leaks the host environment).
            timeout: Wall-clock cap; `docker kill` on expiry (timed_out=True).

        Returns:
            SandboxResult with backend="docker".
        """
        workdir_rel: str | None = None
        if cwd is not None:
            target = Path(cwd)
            if not target.is_absolute():
                target = self.workspace_root / target
            target = target.resolve()
            if self.workspace_root != target and self.workspace_root not in target.parents:
                return SandboxResult(
                    backend=self.name, exit_code=-1, meta={"rejected": True},
                    stderr=(f"sandbox: cwd {cwd!r} is outside the sandbox "
                            f"workspace {str(self.workspace_root)!r}"),
                )
            workdir_rel = target.relative_to(self.workspace_root).as_posix()
        argv = self._docker_argv(cmd, timeout)
        container_name = argv[6]  # set by _docker_argv: --name value
        if env:
            for key, value in env.items():
                argv.insert(7, value)
                argv.insert(7, key)
                argv.insert(7, "-e")
        if workdir_rel:
            argv.insert(7, f"/workspace/{workdir_rel}")
            argv.insert(7, "--workdir")
        try:
            completed = subprocess.run(
                argv, capture_output=True, text=True, timeout=timeout + 5,
            )
        except subprocess.TimeoutExpired:
            # The container outlived the cap: hard-kill it by its unique
            # --name so nothing leaks (docker kill also unblocks the CLI).
            subprocess.run(
                ["docker", "kill", container_name],
                capture_output=True, text=True, timeout=10,
            )
            return SandboxResult(
                stdout="", stderr=f"sandbox: command timed out after {timeout}s",
                exit_code=-1, timed_out=True, backend=self.name,
                meta={"killed": f"container {container_name}"},
            )
        except OSError as exc:
            return SandboxResult(backend=self.name, stderr=f"sandbox: {exc}")
        return SandboxResult(
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
            exit_code=completed.returncode,
            backend=self.name,
        )


DEFAULT_LIMITS = {
    "memory_mb": 256,
    "cpus": 0.5,
    "max_processes": 64,
}
