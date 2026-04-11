"""Failing tests for DraftService.

TDD RED phase — these tests must fail until production code is written.
[TS-022, TS-023, TS-024, TS-025, TS-026, TS-027]
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

# ── In-memory repository for service tests ───────────────────────────────


class InMemoryDraftRepository:
    """Simple in-memory implementation of DraftRepositoryPort for unit tests."""

    def __init__(self):
        self._drafts: dict[str, object] = {}

    def save(self, draft) -> None:
        self._drafts[draft.id] = draft

    def load(self, draft_id: str):
        return self._drafts.get(draft_id)

    def delete(self, draft_id: str) -> bool:
        if draft_id in self._drafts:
            del self._drafts[draft_id]
            return True
        return False

    def list_entries(self, project_name: str | None = None):
        from domain.models.draft import DraftManifestEntry

        entries = []
        for d in self._drafts.values():
            if project_name and d.project_name != project_name:
                continue
            entries.append(
                DraftManifestEntry(
                    id=d.id,
                    project_name=d.project_name,
                    generation_id=d.generation_id,
                    created_at=d.created_at.isoformat(),
                    updated_at=d.updated_at.isoformat(),
                    summary=d.summary,
                )
            )
        entries.sort(key=lambda e: e.created_at, reverse=True)
        return entries

    def find_by_generation_id(self, generation_id: str):
        for d in self._drafts.values():
            if d.generation_id == generation_id:
                return d
        return None


@pytest.fixture
def draft_repo():
    return InMemoryDraftRepository()


@pytest.fixture
def draft_service(draft_repo):
    from services.draft_service import DraftService

    return DraftService(repository=draft_repo)


# ── TS-022: create_draft() persists and returns with computed summary ────


def test_create_draft_persists_and_returns(draft_service, draft_repo, make_domain_analysis):
    """TS-022: create_draft() returns draft with computed summary and persists it."""
    analysis = make_domain_analysis(num_aggregates=3, num_events=8, num_commands=5)
    gen_id = "gen-abc"

    draft = draft_service.create_draft(analysis, gen_id)

    assert draft.generation_id == gen_id
    assert draft.summary.aggregate_count == 3
    assert draft.summary.event_count == 8
    assert draft.summary.command_count == 5
    assert draft.created_at == draft.updated_at
    assert draft_repo.load(draft.id) is not None


# ── TS-023: delete_draft() returns correct boolean ───────────────────────


def test_delete_draft_existing(draft_service, make_domain_analysis):
    """TS-023: delete_draft() returns True for existing draft."""
    analysis = make_domain_analysis()
    draft = draft_service.create_draft(analysis, str(uuid.uuid4()))
    assert draft_service.delete_draft(draft.id) is True


def test_delete_draft_nonexistent(draft_service):
    """TS-023: delete_draft() returns False for non-existent draft."""
    assert draft_service.delete_draft("missing-id") is False


# ── TS-024: update_draft_snapshot() updates snapshot and summary ─────────


def test_update_draft_snapshot(draft_service, make_domain_analysis):
    """TS-024: update_draft_snapshot() updates snapshot, summary, updated_at."""
    original = make_domain_analysis(num_aggregates=3, num_events=8, num_commands=5)
    gen_id = "gen-xyz"
    draft = draft_service.create_draft(original, gen_id)
    original_updated_at = draft.updated_at

    updated = make_domain_analysis(num_aggregates=2, num_events=4, num_commands=3)
    result = draft_service.update_draft_snapshot(gen_id, updated)

    assert result is not None
    assert result.summary.aggregate_count == 2
    assert result.summary.event_count == 4
    assert result.summary.command_count == 3
    assert result.updated_at >= original_updated_at
    assert result.created_at == draft.created_at


# ── TS-025: update_draft_snapshot() returns None for unknown gen ─────────


def test_update_draft_snapshot_unknown_generation(draft_service, make_domain_analysis):
    """TS-025: update_draft_snapshot() returns None when no matching generation."""
    analysis = make_domain_analysis()
    result = draft_service.update_draft_snapshot("gen-unknown", analysis)
    assert result is None


# ── TS-026: get_draft() returns full draft with snapshot ─────────────────


def test_get_draft_returns_full(draft_service, make_domain_analysis):
    """TS-026: get_draft() returns full draft with populated snapshot."""
    analysis = make_domain_analysis()
    draft = draft_service.create_draft(analysis, str(uuid.uuid4()))

    loaded = draft_service.get_draft(draft.id)
    assert loaded is not None
    assert loaded.id == draft.id
    assert loaded.snapshot is not None
    assert len(loaded.snapshot) > 0


# ── TS-027: list_drafts() sorted descending, scoped by project ──────────


def test_list_drafts_sorted_and_scoped(draft_service, make_domain_analysis):
    """TS-027: list_drafts() returns sorted, project-scoped entries."""
    datetime.now(timezone.utc)

    # Create 3 drafts for MyProject at different times
    for i in range(3):
        analysis = make_domain_analysis(project_name="MyProject")
        draft_service.create_draft(analysis, str(uuid.uuid4()))

    # Create 1 draft for OtherProject
    other = make_domain_analysis(project_name="OtherProject")
    draft_service.create_draft(other, str(uuid.uuid4()))

    entries = draft_service.list_drafts(project_name="MyProject")
    assert len(entries) == 3
    # Sorted newest first
    for i in range(len(entries) - 1):
        assert entries[i].created_at >= entries[i + 1].created_at
