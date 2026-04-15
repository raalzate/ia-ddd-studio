"""Pydantic models for agent tool operations and refinement sessions.

Defines ToolResult, OperationRecord, ToolExecution, AgentResponse,
Ambiguity, CompletenessGap, RefinementPlan, and RefinementSession.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Standardized tool execution result."""

    success: bool
    message: str
    affected_elements: list[str] = Field(default_factory=list)


class OperationRecord(BaseModel):
    """Record of a write operation for undo support."""

    timestamp: str
    tool_name: str
    description: str
    snapshot: dict


class ToolExecution(BaseModel):
    """Record of a single tool call within an agent turn."""

    tool_name: str
    arguments: dict
    result: str
    success: bool


class AgentResponse(BaseModel):
    """Response from a single agent turn."""

    content: str
    tool_executions: list[ToolExecution] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# T002: Ambiguity and CompletenessGap models
# ---------------------------------------------------------------------------


class Ambiguity(BaseModel):
    """A detected ambiguity or issue requiring human resolution."""

    id: str
    type: Literal["lexical", "structural", "semantic"]
    priority: Literal[1, 2, 3]  # 1=structural, 2=lexical, 3=cosmetic
    description: str
    affected_elements: list[str]
    suggested_resolutions: list[str]
    assumptions_made: str | None = None
    status: Literal["pending", "resolved", "skipped"] = "pending"


class CompletenessGap(BaseModel):
    """A structural gap detected by completeness analysis."""

    rule_name: str
    description: str
    affected_aggregate: str
    affected_elements: list[str]
    suggestion: str


# ---------------------------------------------------------------------------
# T003: RefinementPlan and RefinementSession models
# ---------------------------------------------------------------------------


class RefinementPlan(BaseModel):
    """Coordinated set of operations to resolve ambiguities."""

    id: str = Field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:8]}")
    source_ambiguity_ids: list[str]
    description: str
    proposed_operations: list[dict]
    status: Literal["pending", "approved", "rejected", "executed", "failed"] = "pending"
    executed_results: list[ToolExecution] = Field(default_factory=list)


class RefinementSession(BaseModel):
    """Tracks a complete post-generation refinement cycle."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    model_hash: str
    ambiguities: list[Ambiguity] = Field(default_factory=list)
    plans: list[RefinementPlan] = Field(default_factory=list)
    status: Literal["analyzing", "presenting", "resolving", "completed"] = "analyzing"

    # ------------------------------------------------------------------
    # Iteration helpers
    # ------------------------------------------------------------------

    def current_ambiguity(self) -> Ambiguity | None:
        """Return the first pending ambiguity, or None if all resolved."""
        for a in self.ambiguities:
            if a.status == "pending":
                return a
        return None

    def pending_count(self) -> int:
        return sum(1 for a in self.ambiguities if a.status == "pending")

    def resolved_count(self) -> int:
        return sum(1 for a in self.ambiguities if a.status in ("resolved", "skipped"))

    def total_count(self) -> int:
        return len(self.ambiguities)

    def is_complete(self) -> bool:
        return all(a.status in ("resolved", "skipped") for a in self.ambiguities)

    def resolve_current(self, skipped: bool = False) -> Ambiguity | None:
        """Mark the first pending ambiguity as resolved/skipped and return the next pending."""
        for a in self.ambiguities:
            if a.status == "pending":
                a.status = "skipped" if skipped else "resolved"
                break
        return self.current_ambiguity()

    @staticmethod
    def compute_model_hash(model_json: str) -> str:
        """Compute SHA-256 hash of a serialized model."""
        return hashlib.sha256(model_json.encode()).hexdigest()
