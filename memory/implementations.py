"""Concrete memory backends: InMemoryMemory (working) and FileMemory (stub)."""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any

from memory.base import Memory, MemoryHit, MemoryRecord


class InMemoryMemory(Memory):
    """List-backed memory with naive keyword matching.

    Good enough for demos and tests; data lives only for the process lifetime.
    """

    def __init__(self) -> None:
        """Start with an empty store."""
        self._records: dict[str, MemoryRecord] = {}

    def write(self, content: str, meta: dict[str, Any] | None = None) -> str:
        """Store content under a fresh uuid id.

        Args:
            content: Text payload.
            meta: Optional metadata.

        Returns:
            The new record id.
        """
        memory_id = uuid.uuid4().hex
        self._records[memory_id] = MemoryRecord(
            id=memory_id, content=content, meta=dict(meta or {})
        )
        return memory_id

    def search(self, query: str, top_k: int = 5) -> list[MemoryHit]:
        """Keyword-overlap search (case-insensitive, whitespace tokenized).

        Args:
            query: Free-text query.
            top_k: Max hits.

        Returns:
            Hits with score = matched query tokens / total query tokens,
            descending. Records with zero overlap are excluded.
        """
        # TODO: replace naive scoring with embeddings or BM25.
        tokens = [t for t in re.split(r"\s+", query.lower()) if t]
        if not tokens:
            return []
        hits: list[MemoryHit] = []
        for record in self._records.values():
            text = record.content.lower()
            matched = sum(1 for tok in set(tokens) if tok in text)
            if matched > 0:
                hits.append(MemoryHit(record=record, score=matched / len(set(tokens))))
        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[:top_k]

    def read(self, memory_id: str) -> MemoryRecord | None:
        """Return the record for `memory_id`, or None.

        Args:
            memory_id: Record id.

        Returns:
            MemoryRecord or None.
        """
        return self._records.get(memory_id)

    def delete(self, memory_id: str) -> bool:
        """Remove a record; True if it existed.

        Args:
            memory_id: Record id.

        Returns:
            Deletion success.
        """
        return self._records.pop(memory_id, None) is not None

    def compact(self) -> int:
        """Drop exact-duplicate contents, keeping the earliest copy.

        Returns:
            Number of records removed.
        """
        # TODO: merge near-duplicates instead of exact matches only.
        seen: set[str] = set()
        removed = 0
        for memory_id in list(self._records):
            content = self._records[memory_id].content
            if content in seen:
                del self._records[memory_id]
                removed += 1
            else:
                seen.add(content)
        return removed


class FileMemory(Memory):
    """Markdown-file-backed memory (stub).

    Each record is one ``<id>.md`` file inside ``root``; content is the
    record body and metadata lives in a small YAML-ish front matter block.
    """

    def __init__(self, root: str | Path) -> None:
        """Create the storage directory if needed.

        Args:
            root: Directory where memory files are stored.
        """
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def write(self, content: str, meta: dict[str, Any] | None = None) -> str:
        """Persist one markdown file per memory.

        Args:
            content: Text payload.
            meta: Optional metadata stored in front matter.

        Returns:
            The new record id (also the filename stem).
        """
        memory_id = uuid.uuid4().hex
        path = self.root / f"{memory_id}.md"
        # TODO: proper YAML escaping for meta values containing colons/quotes.
        front = "\n".join(f"{key}: {value}" for key, value in (meta or {}).items())
        path.write_text(f"---\n{front}\n---\n\n{content}\n", encoding="utf-8")
        return memory_id

    def search(self, query: str, top_k: int = 5) -> list[MemoryHit]:
        """Search stored files.

        Args:
            query: Free-text query.
            top_k: Max hits.

        Returns:
            Not implemented yet — always returns [].

        Raises:
            NotImplementedError: Until the TODO below is done.
        """
        # TODO: scan self.root, parse front matter + body, score like InMemoryMemory.
        raise NotImplementedError("FileMemory.search is a TODO")

    def read(self, memory_id: str) -> MemoryRecord | None:
        """Load a record from its markdown file.

        Args:
            memory_id: Record id (filename stem).

        Returns:
            MemoryRecord or None if missing.
        """
        # TODO: parse front matter back into meta dict.
        path = self.root / f"{memory_id}.md"
        if not path.is_file():
            return None
        text = path.read_text(encoding="utf-8")
        return MemoryRecord(id=memory_id, content=text, meta={})

    def delete(self, memory_id: str) -> bool:
        """Delete the record's file if present.

        Args:
            memory_id: Record id.

        Returns:
            True if a file was removed.
        """
        path = self.root / f"{memory_id}.md"
        if path.is_file():
            path.unlink()
            return True
        return False
