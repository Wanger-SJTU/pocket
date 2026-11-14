"""Sandbox abstraction for tool command execution.

A Sandbox is the "second wall" behind the command blocklist: every
shell/exec tool funnels through this interface so the execution backend
(local subprocess with rlimits, or a Docker container) is swappable
without touching the tools themselves.

Contract (same style as memory/base.py or harness/base.py):

    result = sandbox.run(cmd, cwd=None, env=None, timeout=30.0)
    result.stdout / result.stderr / result.exit_code / result.timed_out

Every layer only depends on this interface — backends are selected at
registration/wiring time (see sandbox/factory.py and main.py).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class SandboxUnavailable(RuntimeError):
    """Raised when a sandbox backend cannot run (e.g. no Docker daemon).

    Callers may catch this and degrade to a weaker backend (Docker ->
    Local) instead of failing the whole run.
    """


@dataclass
class SandboxResult:
    """Outcome of one sandboxed command execution.

    Attributes:
        stdout: Decoded standard output (never None).
        stderr: Decoded standard error (never None).
        exit_code: Process exit code; -1 when killed/timed out/failed to start.
        timed_out: True when the command was killed after exceeding timeout.
        backend: Name of the sandbox backend that ran the command.
        meta: Backend-specific extras (e.g. signal that killed the process).
    """

    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    timed_out: bool = False
    backend: str = ""
    meta: dict = field(default_factory=dict)

    def combined(self) -> str:
        """Return stdout+stderr joined, for tools that want one string."""
        return (self.stdout + self.stderr).strip()


class Sandbox(ABC):
    """Abstract execution backend: run a shell command, confined."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Backend identifier used in SandboxResult.backend and logs."""
        raise NotImplementedError

    @abstractmethod
    def run(
        self,
        cmd: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout: float = 30.0,
    ) -> SandboxResult:
        """Execute `cmd` inside the sandbox.

        Args:
            cmd: Shell command string (run via /bin/sh inside the sandbox).
            cwd: Requested working directory; must resolve inside the
                sandbox's allowed workspace (backends enforce this).
            env: Extra environment variables for this run only; filtered
                against the backend's env whitelist.
            timeout: Max wall-clock seconds; exceeding it kills the process
                (whole process group / container) and sets timed_out=True.

        Returns:
            SandboxResult; implementations never raise for command-level
            failures (non-zero exit), only for setup problems.
        """
        raise NotImplementedError
