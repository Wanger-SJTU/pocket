"""Entry point: wire up config, stub LLM client, tools, and run the loop."""

from __future__ import annotations

import logging

from config import Config
from core.loop import AgentLoop
from llm.client import StubLLMClient
from memory.implementations import InMemoryMemory
from tools.examples import default_registry
from tools.memory_tools import build_memory_tools


def main() -> None:
    """Run a demo agent loop with the stub client."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    # Memory layer: inject a backend and expose memory_write/memory_search
    # tools to the agent (see memory/ and README "Memory 层").
    memory = InMemoryMemory()
    memory.write("The project README describes the agent loop architecture.")

    registry = default_registry()
    for tool in build_memory_tools(memory):
        registry.register(tool)

    config = Config(max_steps=5)
    loop = AgentLoop(client=StubLLMClient(), registry=registry, config=config)

    result = loop.run(task="Read README.md and summarize it.")
    print(f"stop_reason: {result.stop_reason}")
    print(f"steps:      {result.steps}")
    print(f"output:     {result.output}")

    # Gateway demo: IM message in -> AgentLoop -> reply back out (EchoGateway,
    # offline; see README "Gateway 层").
    from gateway.demo import run_gateway_demo

    run_gateway_demo()


if __name__ == "__main__":
    main()
