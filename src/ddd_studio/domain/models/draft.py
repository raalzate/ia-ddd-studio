"""Draft domain models — Pydantic v2 models for generation history drafts.

Entities: Draft, DraftSummary, DraftManifest, DraftManifestEntry.
Helper: compute_summary(DomainAnalysis) -> DraftSummary.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class DraftSummary(BaseModel):
    """Lightweight metadata for sidebar rendering."""

    aggregate_count: int = Field(..., ge=0)
    event_count: int = Field(..., ge=0)
    command_count: int = Field(..., ge=0)
    node_total: int = Field(..., ge=0)
    label: str


class Draft(BaseModel):
    """A saved snapshot of a single domain model generation."""

    id: str
    project_name: str
    generation_id: str
    created_at: datetime
    updated_at: datetime
    summary: DraftSummary
    snapshot: dict

    @field_validator("id")
    @classmethod
    def validate_uuid4(cls, v: str) -> str:
        try:
            parsed = uuid.UUID(v, version=4)
        except (ValueError, AttributeError):
            raise ValueError(f"id must be a valid UUID4, got: {v!r}")
        return str(parsed)

    @model_validator(mode="after")
    def validate_timestamps(self) -> Draft:
        if self.created_at > self.updated_at:
            raise ValueError("created_at must be <= updated_at")
        return self


class DraftManifestEntry(BaseModel):
    """Lightweight index entry for fast sidebar rendering."""

    id: str
    project_name: str
    generation_id: str
    created_at: str
    updated_at: str
    summary: DraftSummary


class DraftManifest(BaseModel):
    """Index file for the drafts directory."""

    version: str = "1.0"
    entries: list[DraftManifestEntry] = Field(default_factory=list)


def compute_summary(analysis) -> DraftSummary:
    """Compute a DraftSummary from a DomainAnalysis instance."""
    all_nodes = list(analysis.big_picture.nodos)
    for agg in analysis.agregados:
        all_nodes.extend(agg.nodos)

    events = sum(1 for n in all_nodes if n.tipo_elemento == "Evento")
    commands = sum(1 for n in all_nodes if n.tipo_elemento == "Comando")

    return DraftSummary(
        aggregate_count=len(analysis.agregados),
        event_count=events,
        command_count=commands,
        node_total=len(all_nodes),
        label=f"{len(analysis.agregados)} aggregates, {events} events, {commands} commands",
    )
