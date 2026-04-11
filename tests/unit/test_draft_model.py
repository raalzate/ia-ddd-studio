"""Failing tests for Draft, DraftSummary, DraftManifest, DraftManifestEntry models.

TDD RED phase — these tests must fail until production code is written.
[TS-028, TS-029, TS-030, TS-031, TS-032, TS-033]
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

# ── TS-028: Draft requires a valid UUID4 id ──────────────────────────────


def test_draft_rejects_invalid_uuid_id():
    """TS-028: Draft with non-UUID id raises ValidationError."""
    from domain.models.draft import Draft

    now = datetime.now(timezone.utc)
    with pytest.raises(Exception):  # ValidationError
        Draft(
            id="not-a-uuid",
            project_name="Test",
            generation_id=str(uuid.uuid4()),
            created_at=now,
            updated_at=now,
            summary=_make_summary(),
            snapshot=_make_snapshot_dict(),
        )


def test_draft_accepts_valid_uuid4_id():
    """TS-028: Draft with valid UUID4 id succeeds."""
    from domain.models.draft import Draft

    now = datetime.now(timezone.utc)
    draft = Draft(
        id=str(uuid.uuid4()),
        project_name="Test",
        generation_id=str(uuid.uuid4()),
        created_at=now,
        updated_at=now,
        summary=_make_summary(),
        snapshot=_make_snapshot_dict(),
    )
    assert draft.id is not None


# ── TS-029: created_at must not be later than updated_at ─────────────────


def test_draft_rejects_created_at_after_updated_at():
    """TS-029: created_at > updated_at raises ValidationError."""
    from domain.models.draft import Draft

    now = datetime.now(timezone.utc)
    with pytest.raises(Exception):
        Draft(
            id=str(uuid.uuid4()),
            project_name="Test",
            generation_id=str(uuid.uuid4()),
            created_at=now + timedelta(hours=1),
            updated_at=now,
            summary=_make_summary(),
            snapshot=_make_snapshot_dict(),
        )


# ── TS-030: Snapshot must be deserializable via DomainAnalysis ───────────


def test_draft_snapshot_deserializable(sample_domain_analysis):
    """TS-030: snapshot can round-trip through DomainAnalysis."""
    from domain.models.draft import Draft
    from models.domain_analysis import DomainAnalysis

    now = datetime.now(timezone.utc)
    snapshot = sample_domain_analysis.model_dump()
    draft = Draft(
        id=str(uuid.uuid4()),
        project_name="Test",
        generation_id=str(uuid.uuid4()),
        created_at=now,
        updated_at=now,
        summary=_make_summary(),
        snapshot=snapshot,
    )
    restored = DomainAnalysis.model_validate(draft.snapshot)
    assert restored.nombre_proyecto == sample_domain_analysis.nombre_proyecto


# ── TS-031: DraftSummary label computed correctly ────────────────────────


def test_compute_summary_counts(make_domain_analysis):
    """TS-031: compute_summary returns correct counts and label."""
    from domain.models.draft import compute_summary

    analysis = make_domain_analysis(
        num_aggregates=3,
        num_events=8,
        num_commands=5,
    )
    summary = compute_summary(analysis)
    assert summary.aggregate_count == 3
    assert summary.event_count == 8
    assert summary.command_count == 5
    assert summary.label == "3 aggregates, 8 events, 5 commands"


# ── TS-032: Missing required field raises error ──────────────────────────


def test_draft_missing_generation_id():
    """TS-032: Draft without generation_id raises ValidationError."""
    from domain.models.draft import Draft

    now = datetime.now(timezone.utc)
    with pytest.raises(Exception):
        Draft(
            id=str(uuid.uuid4()),
            project_name="Test",
            # generation_id missing
            created_at=now,
            updated_at=now,
            summary=_make_summary(),
            snapshot=_make_snapshot_dict(),
        )


# ── TS-033: DraftSummary counts must be non-negative ────────────────────


@pytest.mark.parametrize(
    "field,value",
    [
        ("aggregate_count", -1),
        ("event_count", -5),
        ("command_count", -2),
        ("node_total", -10),
    ],
)
def test_draft_summary_rejects_negative_counts(field, value):
    """TS-033: DraftSummary rejects negative count values."""
    from domain.models.draft import DraftSummary

    payload = {
        "aggregate_count": 0,
        "event_count": 0,
        "command_count": 0,
        "node_total": 0,
        "label": "test",
    }
    payload[field] = value
    with pytest.raises(Exception):
        DraftSummary(**payload)


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_summary():
    """Build a minimal DraftSummary dict for test payloads."""
    from domain.models.draft import DraftSummary

    return DraftSummary(
        aggregate_count=1,
        event_count=2,
        command_count=1,
        node_total=4,
        label="1 aggregates, 2 events, 1 commands",
    )


def _make_snapshot_dict():
    """Build a minimal snapshot dict that DomainAnalysis can validate."""
    from tests.conftest import _make_sample_domain_analysis

    return _make_sample_domain_analysis().model_dump()
