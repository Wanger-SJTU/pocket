"""Entry point: wire up config file/settings, LLM client (real if configured, stub otherwise), tools, and run the loop."""

from __future__ import annotations

import logging
import os

from config import Config, load_settings
from core.loop import AgentLoop
from llm.client import LLMClient, RealLLMClient, StubLLMClient
from memory.implementations import InMemoryMemory
from memory.summarizer import HeuristicSummarizer
from sandbox import create_sandbox
from tools.examples import default_registry
from tools.memory_tools import build_memory_tools

DEFAULT_TASK = "Read README.md and summarize it."


def build_client(settings: dict) -> tuple[LLMClient, str]:
    """Pick the LLM client: RealLLMClient when configured, else stub.

    Args:
        settings: Parsed config.json contents (may be empty).

    Returns:
        (client, mode) where mode describes the choice for logging.
    """
    real = RealLLMClient.from_settings(settings)
    if real is not None:
        return real, f"real ({real.base_url}, model={real.model or 'server default'})"
    hint = "set llm.api_key in config.json (or LLM_API_KEY env) to go real"
    return StubLLMClient(), f"stub ({hint})"


def main() -> None:
    """Run a demo agent loop with the selected client."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    settings, config_path = load_settings()
    print(f"[main] config file: {config_path or '(none — built-in defaults + env vars)'}")

    client, mode = build_client(settings)
    print(f"[main] LLM client: {mode}")
    task = os.environ.get("AGENT_TASK") or str(settings.get("task") or "") or DEFAULT_TASK

    # Memory layer: inject a backend and expose memory_write/memory_search
    # tools to the agent (see memory/ and README "Memory 层").
    memory = InMemoryMemory()
    memory.write("The project README describes the agent loop architecture.")

    # Sandbox layer: pick the backend from config (docker degrades to local
    # when the daemon is down; see README "Sandbox 层").
    config = Config.from_settings(settings)
    sandbox = create_sandbox(config.sandbox.to_settings(), config.sandbox.workspace_root)
    print(f"[main] sandbox backend: {sandbox.name} (workspace: {config.sandbox.workspace_root})")
    registry = default_registry(sandbox=sandbox)
    for tool in build_memory_tools(memory):
        registry.register(tool)

    config.model_name = getattr(client, "model", "") or config.model_name or "stub-model"
    loop = AgentLoop(client=client, registry=registry, config=config,
                     summarizer=HeuristicSummarizer())

    result = loop.run(task=task)
    print(f"stop_reason: {result.stop_reason}")
    print(f"steps:      {result.steps}")
    print(f"output:     {result.output}")

    # Gateway demo: IM message in -> AgentLoop -> reply back out (EchoGateway,
    # offline; see README "Gateway 层").
    from gateway.demo import run_gateway_demo

    run_gateway_demo()


if __name__ == "__main__":
    main()
