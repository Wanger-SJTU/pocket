"""LocalSandbox: run commands as local subprocesses inside a constrained jail.

Defenses layered here (all stdlib):

- workspace whitelist: cwd must resolve inside workspace_root; a per-run
  temp dir is created inside it when no cwd is given
- env whitelist: only whitelisted variable names pass through to the child
- rlimits (resource.setrlimit in preexec_fn): CPU seconds, address space,
  output file size, and process count — so forks/bombs fail fast
- process-group kill: the child starts in its own process group (start_new_session)
  and the whole group is killed on timeout
"""

from __future__ import annotations

import logging
import os
import resource
import signal
import subprocess
import tempfile
from pathlib import Path

from sandbox.base import Sandbox, SandboxResult

logger = logging.getLogger(__name__)

# Env vars a sandboxed command is allowed to see. Everything else is
# stripped — secrets in the parent env never reach the child.
DEFAULT_ENV_WHITELIST = ("PATH", "HOME", "LANG", "LC_ALL", "TERM", "TMPDIR")


class LocalSandbox(Sandbox):
    """Confining subprocess backend; the weakest wall, but always available."""

    def __init__(
        self,
        workspace_root: str | Path,
        limits: dict | None = None,
        env_whitelist: tuple[str, ...] = DEFAULT_ENV_WHITELIST,
    ) -> None:
        """Bind the sandbox to a workspace and resource limits.

        Args:
            workspace_root: Only directories inside this tree are legal cwds;
                it is created if missing.
            limits: Optional overrides: cpu_seconds, memory_mb, file_size_mb,
                max_processes (see DEFAULT_LIMITS).
            env_whitelist: Env variable names passed through to the child.
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.limits = {**DEFAULT_LIMITS, **(limits or {})}
        self.env_whitelist = env_whitelist

    @property
    def name(self) -> str:
        """Backend identifier."""
        return "local"

    def _resolve_cwd(self, cwd: str | None) -> Path:
        """Map a requested cwd to a safe directory inside the workspace.

        Args:
            cwd: Requested directory, absolute or workspace-relative.

        Returns:
            Resolved directory guaranteed to be inside workspace_root.

        Raises:
            PermissionError: If the request resolves outside the workspace.
        """
        if cwd is None:
            run_dir = Path(tempfile.mkdtemp(prefix="run-", dir=self.workspace_root))
            return run_dir
        target = Path(cwd)
        if not target.is_absolute():
            target = self.workspace_root / target
        target = target.resolve()
        if self.workspace_root != target and self.workspace_root not in target.parents:
            raise PermissionError(
                f"cwd {cwd!r} is outside the sandbox workspace "
                f"{str(self.workspace_root)!r}"
            )
        return target

    def _child_env(self, env: dict[str, str] | None) -> dict[str, str]:
        """Build a whitelisted environment for the child process.

        Args:
            env: Extra variables requested for this run (whitelisted names only).

        Returns:
            Minimal env dict; PATH is ensured so `sh -c` finds basic binaries.
        """
        child = {k: os.environ[k] for k in self.env_whitelist if k in os.environ}
        child.setdefault("PATH", "/usr/local/bin:/usr/bin:/bin")
        child.setdefault("HOME", str(self.workspace_root))
        for key, value in (env or {}).items():
            if key in self.env_whitelist:
                child[key] = value
        return child

    def _preexec(self) -> None:  # pragma: no cover - runs in the child
        """Apply rlimits in the child before exec (preexec_fn callback)."""
        cpu = int(self.limits.get("cpu_seconds", 10))
        mem_bytes = int(self.limits.get("memory_mb", 256)) * 1024 * 1024
        file_bytes = int(self.limits.get("file_size_mb", 64)) * 1024 * 1024
        max_procs = int(self.limits.get("max_processes", 64))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        resource.setrlimit(resource.RLIMIT_FSIZE, (file_bytes, file_bytes))
        resource.setrlimit(resource.RLIMIT_NPROC, (max_procs, max_procs))

    def run(
        self,
        cmd: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout: float = 30.0,
    ) -> SandboxResult:
        """Run `cmd` via sh -c with the jail applied (see class docstring).

        Args:
            cmd: Shell command string.
            cwd: Requested working directory inside the workspace.
            env: Extra env vars (whitelisted names only).
            timeout: Wall-clock cap; the process group is killed on expiry.

        Returns:
            SandboxResult with backend="local"; timed_out=True after a kill.
        """
        try:
            workdir = self._resolve_cwd(cwd)
        except PermissionError as exc:
            return SandboxResult(backend=self.name, stderr=f"sandbox: {exc}",
                                 exit_code=-1, meta={"rejected": True})
        try:
            proc = subprocess.Popen(
                ["/bin/sh", "-c", cmd],
                cwd=str(workdir),
                env=self._child_env(env),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,  # own process group -> group kill works
                preexec_fn=self._preexec,
            )
        except OSError as exc:
            return SandboxResult(backend=self.name, stderr=f"sandbox: {exc}")
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            return SandboxResult(
                stdout=stdout or "", stderr=stderr or "",
                exit_code=proc.returncode if proc.returncode is not None else -1,
                backend=self.name,
            )
        except subprocess.TimeoutExpired:
            # Kill the whole process group: shell + every descendant.
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = proc.communicate()
            return SandboxResult(
                stdout=stdout or "", stderr=stderr or "", exit_code=-1,
                timed_out=True, backend=self.name,
                meta={"killed": f"process group after {timeout}s timeout"},
            )


# Sane defaults; overridable via config sandbox.limits.
# NOTE: RLIMIT_NPROC is per-real-UID on Linux, not per-sandbox — a limit
# below the user's CURRENT process count makes every fork fail (child can't
# even start; the count drifts as the host churns). Keep it comfortably above
# the busy-host floor: it still turns fork bombs into EAGAIN failures without
# bricking normal runs. For a hard per-sandbox process cap use the docker
# backend (--pids-limit is per-container).
DEFAULT_LIMITS = {
    "cpu_seconds": 10,     # RLIMIT_CPU
    "memory_mb": 256,      # RLIMIT_AS
    "file_size_mb": 64,    # RLIMIT_FSIZE (output files)
    "max_processes": 1024, # RLIMIT_NPROC (per-UID! see note above)
}
