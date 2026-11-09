"""Memory abstraction: persistent/ephemeral storage the agent can read & search.

This layer sits beside the tool layer — it does NOT alter the core loop.
Implementations plug in via the `Memory` interface; tools (see
tools/memory_tools.py) expose memory ops to the LLM, and main.py injects
the chosen backend into the AgentLoop.
"""

from memory.base import Memory, MemoryHit, MemoryRecord  # noqa: F401
