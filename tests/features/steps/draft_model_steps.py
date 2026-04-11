"""BDD step definitions for draft-model-validation.feature.

[TS-028, TS-029, TS-030, TS-031, TS-032, TS-033]
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from domain.models.draft import Draft, DraftSummary, compute_summary
from models.domain_analysis import DomainAnalysis
from tests.conftest import FEATURE_005_DIR, _make_sample_domain_analysis

scenarios(f"{FEATURE_005_DIR}/draft-model-validation.feature")


# ── Shared context ───────────────────────────────────────────────────────


@pytest.fixture
def ctx():
    return {}


def _valid_summary():
    return DraftSummary(
        aggregate_count=1,
        event_count=2,
        command_count=1,
        node_total=4,
        label="1 aggregates, 2 events, 1 commands",
    )


def _valid_snapshot():
    return _make_sample_domain_analysis().model_dump()


# ── TS-028: Draft requires valid UUID4 ───────────────────────────────────


@given('a draft payload where the id field is "not-a-uuid"', target_fixture="ctx")
def draft_payload_invalid_uuid(ctx):
    ctx = {
        "payload": dict(
            id="not-a-uuid",
            project_name="Test",
            generation_id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            summary=_valid_summary(),
            snapshot=_valid_snapshot(),
        )
    }
    return ctx


@when("the Draft model is instantiated with that payload", target_fixture="ctx")
def instantiate_draft(ctx):
    try:
        ctx["draft"] = Draft(**ctx["payload"])
        ctx["error"] = None
    except Exception as e:
        ctx["draft"] = None
        ctx["error"] = e
    return ctx


@then("a validation error is raised indicating the id must be a valid UUID4")
def check_uuid_error(ctx):
    assert ctx["error"] is not None
    assert "uuid" in str(ctx["error"]).lower() or "UUID4" in str(ctx["error"])


# ── TS-029: created_at must not be later than updated_at ─────────────────


@given("a draft payload where created_at is later than updated_at", target_fixture="ctx")
def draft_payload_bad_timestamps(ctx):
    now = datetime.now(timezone.utc)
    ctx = {
        "payload": dict(
            id=str(uuid.uuid4()),
            project_name="Test",
            generation_id=str(uuid.uuid4()),
            created_at=now + timedelta(hours=1),
            updated_at=now,
            summary=_valid_summary(),
            snapshot=_valid_snapshot(),
        )
    }
    return ctx


@then("a validation error is raised indicating created_at must be <= updated_at")
def check_timestamp_error(ctx):
    assert ctx["error"] is not None
    assert "created_at" in str(ctx["error"]).lower() or "updated_at" in str(ctx["error"]).lower()


# ── TS-030: Snapshot deserializable ──────────────────────────────────────


@given("a draft with a valid snapshot stored as a dict", target_fixture="ctx")
def draft_with_valid_snapshot(ctx):
    analysis = _make_sample_domain_analysis()
    now = datetime.now(timezone.utc)
    draft = Draft(
        id=str(uuid.uuid4()),
        project_name="Test",
        generation_id=str(uuid.uuid4()),
        created_at=now,
        updated_at=now,
        summary=_valid_summary(),
        snapshot=analysis.model_dump(),
    )
    return {"draft": draft}


@when("DomainAnalysis.model_validate(draft.snapshot) is called", target_fixture="ctx")
def validate_snapshot(ctx):
    try:
        ctx["restored"] = DomainAnalysis.model_validate(ctx["draft"].snapshot)
        ctx["error"] = None
    except Exception as e:
        ctx["restored"] = None
        ctx["error"] = e
    return ctx


@then("a valid DomainAnalysis instance is returned without errors")
def check_restored(ctx):
    assert ctx["error"] is None
    assert isinstance(ctx["restored"], DomainAnalysis)


# ── TS-031: DraftSummary label computed correctly ────────────────────────


@given(
    parsers.parse("a DomainAnalysis with {agg:d} aggregates, {evt:d} events, and {cmd:d} commands"),
    target_fixture="ctx",
)
def analysis_with_counts(agg, evt, cmd):
    return {
        "analysis": _make_sample_domain_analysis(
            num_aggregates=agg,
            num_events=evt,
            num_commands=cmd,
        )
    }


@when("compute_summary(analysis) is called", target_fixture="ctx")
def call_compute_summary(ctx):
    ctx["summary"] = compute_summary(ctx["analysis"])
    return ctx


@then(
    parsers.parse("the returned DraftSummary has aggregate_count={agg:d}, event_count={evt:d}, command_count={cmd:d}")
)
def check_summary_counts(ctx, agg, evt, cmd):
    s = ctx["summary"]
    assert s.aggregate_count == agg
    assert s.event_count == evt
    assert s.command_count == cmd


@then(parsers.parse('the label field equals "{expected_label}"'))
def check_summary_label(ctx, expected_label):
    assert ctx["summary"].label == expected_label


# ── TS-032: Missing required field ───────────────────────────────────────


@given('a draft payload missing the "generation_id" field', target_fixture="ctx")
def draft_payload_missing_field(ctx):
    now = datetime.now(timezone.utc)
    return {
        "payload": dict(
            id=str(uuid.uuid4()),
            project_name="Test",
            created_at=now,
            updated_at=now,
            summary=_valid_summary(),
            snapshot=_valid_snapshot(),
        )
    }


@then('a validation error is raised indicating "generation_id" is required')
def check_missing_field_error(ctx):
    assert ctx["error"] is not None
    assert "generation_id" in str(ctx["error"])


# ── TS-033: DraftSummary non-negative counts ─────────────────────────────


@given(
    parsers.parse("a DraftSummary payload where {field} is {invalid_value:d}"),
    target_fixture="ctx",
)
def summary_payload_negative(field, invalid_value):
    payload = dict(
        aggregate_count=0,
        event_count=0,
        command_count=0,
        node_total=0,
        label="test",
    )
    payload[field] = invalid_value
    return {"payload": payload, "field": field}


@when("the DraftSummary model is instantiated with that payload", target_fixture="ctx")
def instantiate_summary(ctx):
    try:
        ctx["summary"] = DraftSummary(**ctx["payload"])
        ctx["error"] = None
    except Exception as e:
        ctx["summary"] = None
        ctx["error"] = e
    return ctx


@then(parsers.parse("a validation error is raised for {field}"))
def check_negative_error(ctx, field):
    assert ctx["error"] is not None
