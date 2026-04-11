"""DraftService — orchestrates draft lifecycle operations.

Provides create, list, get, delete, and update operations for generation drafts.
Delegates persistence to an injected DraftRepositoryPort.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from domain.models.draft import (
    Draft,
    DraftManifestEntry,
    compute_summary,
)


class DraftService:
    """Application service for draft lifecycle management."""

    def __init__(self, repository) -> None:
        """Initialize with an injected DraftRepositoryPort."""
        self._repo = repository

    def create_draft(self, analysis, generation_id: str) -> Draft:
        """Create a new draft snapshot from a completed generation.

        Args:
            analysis: The DomainAnalysis produced by the generation.
            generation_id: UUID linking this draft to the generation run.

        Returns:
            The created Draft with computed summary.
        """
        now = datetime.now(timezone.utc)
        summary = compute_summary(analysis)

        draft = Draft(
            id=str(uuid.uuid4()),
            project_name=analysis.nombre_proyecto,
            generation_id=generation_id,
            created_at=now,
            updated_at=now,
            summary=summary,
            snapshot=analysis.model_dump(),
        )
        self._repo.save(draft)
        return draft

    def list_drafts(self, project_name: str | None = None) -> list[DraftManifestEntry]:
        """List draft entries for sidebar display, sorted by created_at descending."""
        return self._repo.list_entries(project_name=project_name)

    def get_draft(self, draft_id: str) -> Draft | None:
        """Load full draft for preview."""
        return self._repo.load(draft_id)

    def delete_draft(self, draft_id: str) -> bool:
        """Delete a draft permanently. Returns True if deleted."""
        return self._repo.delete(draft_id)

    def update_draft_snapshot(self, generation_id: str, updated_analysis) -> Draft | None:
        """Update an existing draft when its linked model is modified.

        Returns the updated Draft if found, None if no matching draft.
        """
        draft = self._repo.find_by_generation_id(generation_id)
        if draft is None:
            return None

        draft.snapshot = updated_analysis.model_dump()
        draft.summary = compute_summary(updated_analysis)
        draft.updated_at = datetime.now(timezone.utc)
        self._repo.save(draft)
        return draft
