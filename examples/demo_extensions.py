"""Demo: wire up skills, plugins, MCP, and the ReviewGate end-to-end (offline).

Run:  python3 -m examples.demo_extensions
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from config import Config, ReviewConfig
from core.loop import AgentLoop
from core.review import ReviewGate, ThresholdReviewer
from llm.client import LLMResponse, StubLLMClient, ToolCall
from mcp.client import StdioMCPClient
from mcp.base import MCPServerConfig
from mcp.registry import MCPToolRegistry
from plugins.base import PluginContext
from plugins.loader import PluginLoader
from skills.manager import SkillManager
from tools.base import ToolRegistry
from tools.examples import default_registry

EXAMPLES_DIR = Path(__file__).resolve().parent


def main() -> None:
    """Assemble every extension point and run three mini-scenarios."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    # 1. Skills: instructions injected into the system prompt.
    skills = SkillManager()
    loaded = skills.discover(EXAMPLES_DIR / "demo_skills")
    print(f"[skills] loaded: {[s.name for s in loaded]}")
    config = Config(max_steps=5, review=ReviewConfig(enabled=False))
    config.system_prompt = skills.inject_instructions(config.system_prompt)

    registry: ToolRegistry = default_registry()

    # 2. Skill tools (this demo skill is instructions-only, so none expected).
    print(f"[skills] tools registered: {skills.register_tools(registry)}")

    # 3. Plugins: lifecycle-managed code extensions.
    loader = PluginLoader()
    gate = ReviewGate([ThresholdReviewer(deny_tools=["echo_upper"])])
    plugin_names = loader.discover(
        EXAMPLES_DIR / "demo_plugins",
        PluginContext(config=config, tool_registry=registry, review_gate=gate),
    )
    print(f"[plugins] loaded: {plugin_names}")

    # 4. MCP: bridge the mock server's tools over stdio JSON-RPC.
    mcp = MCPToolRegistry()
    client = StdioMCPClient(MCPServerConfig(
        name="mock",
        command=sys.executable,
        args=[str(EXAMPLES_DIR / "mock_mcp_server.py")],
    ))
    mcp_tools = mcp.connect(client, "mock", registry)
    print(f"[mcp] tools registered: {mcp_tools}")

    # Scenario A: review layer ON, echo_upper denied -> model gets feedback.
    scripted = StubLLMClient(script=[
        LLMResponse(content="", tool_calls=[
            ToolCall(id="c1", name="echo_upper", arguments='{"text": "hello"}')]),
        LLMResponse(content="Plan was denied; stopping with revised answer."),
    ])
    loop = AgentLoop(client=scripted, registry=registry,
                     config=Config(max_steps=5, review=ReviewConfig(enabled=True)),
                     review_gate=gate)
    result = loop.run(task="call echo_upper with text 'hello'")
    print(f"[review-demo] stop={result.stop_reason} output={result.output!r}")

    # Scenario B: review layer OFF, everything runs.
    scripted2 = StubLLMClient(script=[
        LLMResponse(content="", tool_calls=[
            ToolCall(id="c2", name="mock__reverse", arguments='{"text": "agent-loop"}')]),
        LLMResponse(content="Reversed via MCP tool successfully."),
    ])
    loop2 = AgentLoop(client=scripted2, registry=registry,
                      config=Config(max_steps=5))
    result2 = loop2.run(task="call mock__reverse with text 'agent-loop'")
    print(f"[no-review-demo] stop={result2.stop_reason} output={result2.output!r}")

    loader.teardown_all()
    mcp.close_all()


if __name__ == "__main__":
    main()
