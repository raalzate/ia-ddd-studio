"""Failing tests for FileDraftRepository adapter.

TDD RED phase — these tests must fail until production code is written.
[TS-016, TS-017, TS-018, TS-019, TS-020, TS-021]
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone

# ── Helpers ──────────────────────────────────────────────────────────────


def _make_draft(project_name="TestProject", generation_id=None, created_at=None):
    """Build a valid Draft instance for repository tests."""
    from domain.models.draft import Draft, DraftSummary

    from tests.conftest import _make_sample_domain_analysis

    now = created_at or datetime.now(timezone.utc)
    return Draft(
        id=str(uuid.uuid4()),
        project_name=project_name,
        generation_id=generation_id or str(uuid.uuid4()),
        created_at=now,
        updated_at=now,
        summary=DraftSummary(
            aggregate_count=2,
            event_count=4,
            command_count=3,
            node_total=9,
            label="2 aggregates, 4 events, 3 commands",
        ),
        snapshot=_make_sample_domain_analysis(project_name=project_name).model_dump(),
    )


# ── TS-016: save() creates draft JSON file and manifest entry ────────────


def test_save_creates_draft_file_and_manifest(tmp_drafts_dir):
    """TS-016: save() creates {draft.id}.json and manifest entry."""
    from infra.adapters.file_draft_repository import FileDraftRepository

    repo = FileDraftRepository(drafts_dir=tmp_drafts_dir)
    draft = _make_draft()
    repo.save(draft)

    # Draft file exists
    draft_file = os.path.join(tmp_drafts_dir, f"{draft.id}.json")
    assert os.path.exists(draft_file)

    # Manifest contains entry
    manifest_path = os.path.join(tmp_drafts_dir, "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)
    entry_ids = [e["id"] for e in manifest["entries"]]
    assert draft.id in entry_ids

    # Manifest entry summary matches
    entry = next(e for e in manifest["entries"] if e["id"] == draft.id)
    assert entry["summary"]["aggregate_count"] == draft.summary.aggregate_count


# ── TS-017: delete() removes draft file and manifest entry ───────────────


def test_delete_removes_file_and_manifest_entry(tmp_drafts_dir):
    """TS-017: delete() removes file and manifest entry, returns True."""
    from infra.adapters.file_draft_repository import FileDraftRepository

    repo = FileDraftRepository(drafts_dir=tmp_drafts_dir)
    draft = _make_draft()
    repo.save(draft)

    result = repo.delete(draft.id)
    assert result is True
    assert not os.path.exists(os.path.join(tmp_drafts_dir, f"{draft.id}.json"))

    manifest_path = os.path.join(tmp_drafts_dir, "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)
    entry_ids = [e["id"] for e in manifest["entries"]]
    assert draft.id not in entry_ids


# ── TS-018: list_entries() filters by project and sorts descending ───────


def test_list_entries_filters_by_project_and_sorts(tmp_drafts_dir):
    """TS-018: list_entries(project_name) filters and sorts descending."""
    from infra.adapters.file_draft_repository import FileDraftRepository

    repo = FileDraftRepository(drafts_dir=tmp_drafts_dir)
    now = datetime.now(timezone.utc)

    # Save drafts for two projects
    for i in range(3):
        d = _make_draft(project_name="Alpha", created_at=now + timedelta(minutes=i))
        repo.save(d)
    for i in range(2):
        d = _make_draft(project_name="Beta", created_at=now + timedelta(minutes=i))
        repo.save(d)

    entries = repo.list_entries(project_name="Alpha")
    assert len(entries) == 3
    assert all(e.project_name == "Alpha" for e in entries)
    # Sorted descending by created_at
    for i in range(len(entries) - 1):
        assert entries[i].created_at >= entries[i + 1].created_at


# ── TS-019: find_by_generation_id() returns matching draft ───────────────


def test_find_by_generation_id(tmp_drafts_dir):
    """TS-019: find_by_generation_id returns the correct draft."""
    from infra.adapters.file_draft_repository import FileDraftRepository

    repo = FileDraftRepository(drafts_dir=tmp_drafts_dir)
    gen_id = "gen-123"
    draft = _make_draft(generation_id=gen_id)
    repo.save(draft)

    found = repo.find_by_generation_id(gen_id)
    assert found is not None
    assert found.generation_id == gen_id


# ── TS-020: Corrupted manifest rebuilt from individual files ─────────────


def test_manifest_rebuilt_on_corruption(tmp_drafts_dir):
    """TS-020: Corrupted manifest is rebuilt from draft files on init."""
    from infra.adapters.file_draft_repository import FileDraftRepository

    repo = FileDraftRepository(drafts_dir=tmp_drafts_dir)
    draft = _make_draft()
    repo.save(draft)

    # Corrupt the manifest
    manifest_path = os.path.join(tmp_drafts_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        f.write("CORRUPTED")

    # Re-init should rebuild
    repo2 = FileDraftRepository(drafts_dir=tmp_drafts_dir)
    entries = repo2.list_entries()
    assert len(entries) >= 1
    assert any(e.id == draft.id for e in entries)


# ── TS-021: delete() returns False for non-existent id ───────────────────


def test_delete_returns_false_for_nonexistent(tmp_drafts_dir):
    """TS-021: delete() returns False when id does not exist."""
    from infra.adapters.file_draft_repository import FileDraftRepository

    repo = FileDraftRepository(drafts_dir=tmp_drafts_dir)
    result = repo.delete("non-existent-id")
    assert result is False
