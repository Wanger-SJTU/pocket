"""Sandbox layer: confining execution backends for shell/exec tools.

Public surface (interface-only style, like memory/ or harness/):
    Sandbox, SandboxResult, SandboxUnavailable  (base.py)
    create_sandbox(settings, workspace_root)    (factory.py)
"""

from sandbox.base import Sandbox, SandboxResult, SandboxUnavailable
from sandbox.factory import create_sandbox

__all__ = ["Sandbox", "SandboxResult", "SandboxUnavailable", "create_sandbox"]
