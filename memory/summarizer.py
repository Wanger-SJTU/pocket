"""Context compaction / summarization interface (stub).

The intent: when the running Context approaches its token limit, the loop
(or main.py wiring) can call a Summarizer to compress older history into a
short digest before continuing. Kept separate from `Memory` because
summarization is a strategy (LLM-backed, extractive, ...) rather than storage.

TODO:
    - Define token estimation helper (rough chars/4 heuristic or tokenizer).
    - LLMSummarizer: send old messages to the LLM, replace them with a digest.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.context import Context


class Summarizer(ABC):
    """Abstract context-compaction strategy.

    Implementations receive the live Context and shrink it in place (or
    return a digest for the caller to splice in).
    """

    @abstractmethod
    def should_compact(self, context: Context, token_limit: int) -> bool:
        """Decide whether the context needs compaction.

        Args:
            context: The running conversation.
            token_limit: Max tokens the backend/model tolerates.

        Returns:
            True if compaction should run now.
        """
        raise NotImplementedError

    @abstractmethod
    def compact(self, context: Context) -> str:
        """Compress older history in place.

        Args:
            context: The running conversation; older messages are replaced
                by a single digest message.

        Returns:
            The digest text that replaced the compressed portion.
        """
        raise NotImplementedError


class NoopSummarizer(Summarizer):
    """Default no-op summarizer; never compacts."""

    def should_compact(self, context: Context, token_limit: int) -> bool:
        """Never compacts.

        Args:
            context: Unused.
            token_limit: Unused.

        Returns:
            Always False.
        """
        return False

    def compact(self, context: Context) -> str:
        """Leave context untouched.

        Args:
            context: Unused.

        Returns:
            Empty string.
        """
        return ""
