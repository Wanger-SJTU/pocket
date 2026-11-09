"""Abstract memory interface and data classes.

TODO:
    - Add scoped namespaces (per-session / per-agent memory isolation).
    - Add TTL / expiry semantics for ephemeral memories.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryRecord:
    """A single stored memory item.

    Attributes:
        id: Unique identifier assigned by the backend on write.
        content: The memory payload (usually text).
        meta: Free-form metadata (source, timestamp, tags, ...).
    """

    id: str
    content: str
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryHit:
    """A search result: the matched record plus a relevance score.

    Attributes:
        record: The matched MemoryRecord.
        score: Relevance score in [0, 1]; higher is more relevant.
    """

    record: MemoryRecord
    score: float


class Memory(ABC):
    """Abstract memory backend interface.

    Implementations must be safe to call from the agent loop's tool
    execution path (synchronous, no blocking I/O surprises).
    """

    @abstractmethod
    def write(self, content: str, meta: dict[str, Any] | None = None) -> str:
        """Store a memory and return its assigned id.

        Args:
            content: Text payload to remember.
            meta: Optional metadata dict (tags, source, timestamp).

        Returns:
            The id of the newly stored MemoryRecord.
        """
        raise NotImplementedError

    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> list[MemoryHit]:
        """Search memories by relevance to the query.

        Args:
            query: Free-text query (backend decides matching strategy).
            top_k: Maximum number of hits to return.

        Returns:
            Hits ordered by descending score. Empty list if nothing matches.
        """
        raise NotImplementedError

    @abstractmethod
    def read(self, memory_id: str) -> MemoryRecord | None:
        """Fetch a single memory by id.

        Args:
            memory_id: Id returned by a previous write().

        Returns:
            The MemoryRecord, or None if the id is unknown.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        """Delete a memory by id.

        Args:
            memory_id: Id of the memory to remove.

        Returns:
            True if something was deleted, False if the id was unknown.
        """
        raise NotImplementedError

    def compact(self) -> int:
        """Compress/merge memories to reduce storage and prompt pressure.

        Optional operation; default is a no-op.

        Returns:
            Number of records removed/merged (0 if unsupported).
        """
        # TODO: implement per-backend compaction strategies.
        return 0

    def summarize(self) -> str:
        """Return a compact textual summary of current memory contents.

        Optional operation; default returns an empty string. Intended to be
        injected into the prompt when the context approaches its token limit.

        Returns:
            Summary text (may be empty).
        """
        # TODO: hook into the loop near the token limit; LLM-backed summary.
        return ""
