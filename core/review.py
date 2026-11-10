"""ReviewGate: consult reviewers *before* every tool execution.

Inspired by "show me you want" (sm.yw): instead of discovering a bad change
after it happened, surface the planned action for confirmation first. A
reviewer can approve, deny (with feedback fed back to the LLM), or modify
the arguments on the fly.

Design:
    - AgentLoop._execute consults config.review_gate before calling a tool.
    - Deny results are returned as "review denied: ..." so the model can
      revise its plan in the next iteration — no exception, no crash.
    - Default-off; enable via Config(review=ReviewConfig(enabled=True)).
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class ReviewRequest:
    """A planned tool execution, surfaced for review.

    Attributes:
        tool_name: Name of the tool about to run.
        arguments: Parsed arguments about to be passed.
        reason: Optional explanation from the loop (e.g. call id).
    """

    tool_name: str
    arguments: dict[str, Any]
    reason: str = ""

    def render(self) -> str:
        """Human/model-readable one-screen plan of the pending action."""
        return (f"[review] tool: {self.tool_name}\n"
                f"[review] args: {json.dumps(self.arguments, ensure_ascii=False)}")


@dataclass
class ReviewDecision:
    """Outcome of one review.

    Attributes:
        action: "approve", "deny", or "modify".
        feedback: When denying, why — fed back to the LLM verbatim.
        arguments: When modifying, replacement arguments (approved as-is).
    """

    action: str
    feedback: str = ""
    arguments: dict[str, Any] | None = None


class Reviewer(ABC):
    """Base class for reviewers consulted before tool execution."""

    @abstractmethod
    def review(self, request: ReviewRequest) -> ReviewDecision:
        """Judge one pending tool call."""
        raise NotImplementedError


class AutoApproveReviewer(Reviewer):
    """Approves everything — useful as a no-op default."""

    def review(self, request: ReviewRequest) -> ReviewDecision:
        """Always approve."""
        return ReviewDecision(action="approve")


class DeniedReviewer(Reviewer):
    """Denies everything with fixed feedback — for tests and demos."""

    def __init__(self, feedback: str = "not allowed") -> None:
        """Store the rejection message."""
        self.feedback = feedback

    def review(self, request: ReviewRequest) -> ReviewDecision:
        """Always deny with the configured feedback."""
        return ReviewDecision(action="deny", feedback=self.feedback)


class ThresholdReviewer(Reviewer):
    """Rule-based reviewer: only flag calls matching configured rules.

    Rules are simple substrings matched against the tool name or the raw
    arguments; enough for demos, replaceable by richer policies.
    """

    def __init__(self, deny_tools: list[str] | None = None,
                 require_feedback: str = "this tool requires manual confirmation") -> None:
        """Store deny rules.

        Args:
            deny_tools: Tool names that must be denied.
            require_feedback: Feedback text used on denial.
        """
        self.deny_tools = deny_tools or []
        self.require_feedback = require_feedback

    def review(self, request: ReviewRequest) -> ReviewDecision:
        """Deny blacklisted tools; approve the rest."""
        if request.tool_name in self.deny_tools:
            return ReviewDecision(action="deny",
                                  feedback=f"{request.tool_name}: {self.require_feedback}")
        return ReviewDecision(action="approve")


class ReviewGate:
    """Aggregates reviewers; first non-approve decision wins.

    Listeners (e.g. plugin hooks) observe every request and may return a
    decision themselves; reviewers added via add_reviewer run afterwards.
    """

    def __init__(self, reviewers: list[Reviewer] | None = None,
                 enabled: bool = True) -> None:
        """Optionally seed with reviewers.

        Args:
            reviewers: Initial reviewer list.
            enabled: When False, check() short-circuits to approve.
        """
        self.enabled = enabled
        self._reviewers: list[Reviewer] = list(reviewers or [])
        self._listeners: list[Callable[[ReviewRequest], ReviewDecision | None]] = []

    def add_reviewer(self, reviewer: Reviewer) -> None:
        """Register a reviewer."""
        self._reviewers.append(reviewer)

    def add_listener(self, callback: Callable[[ReviewRequest], ReviewDecision | None]) -> None:
        """Register an observer callback (may return a decision or None)."""
        self._listeners.append(callback)

    def check(self, request: ReviewRequest) -> ReviewDecision:
        """Run listeners then reviewers; return the binding decision.

        Returns:
            First deny/modify encountered, else approve. A disabled gate
            approves everything without consulting anyone.
        """
        if not self.enabled:
            return ReviewDecision(action="approve")
        logger.info("review: %s", request.render())
        logger.info("review: %s", request.render())
        for listener in self._listeners:
            decision = listener(request)
            if decision is not None and decision.action != "approve":
                return decision
        for reviewer in self._reviewers:
            decision = reviewer.review(request)
            if decision.action != "approve":
                return decision
        return ReviewDecision(action="approve")
