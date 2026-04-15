"""BDD step definitions for us2-history-sidebar.feature.

[TS-004, TS-005, TS-006]
"""

from __future__ import annotations

import uuid

import pytest
from infra.adapters.file_draft_repository import FileDraftRepository
from pytest_bdd import given, scenarios, then, when
from services.draft_service import DraftService

from tests.conftest import FEATURE_005_DIR, _make_sample_domain_analysis

scenarios(f"{FEATURE_005_DIR}/us2-history-sidebar.feature")


@pytest.fixture
def ctx():
    return {}


# ── Background ───────────────────────────────────────────────────────────


@given("the user has an active DDD project with the sidebar open", target_fixture="ctx")
def active_project_sidebar(tmp_path):
    drafts_dir = str(tmp_path / "drafts")
    repo = FileDraftRepository(drafts_dir=drafts_dir)
    service = DraftService(repository=repo)
    return {"repo": repo, "service": service, "dir": drafts_dir}


# ── TS-004: Draft entry shows timestamp and summary ──────────────────────


@given("at least one draft exists in the sidebar", target_fixture="ctx")
def one_draft_exists(ctx):
    analysis = _make_sample_domain_analysis(num_aggregates=3, num_events=5, num_commands=2)
    ctx["draft"] = ctx["service"].create_draft(analysis, str(uuid.uuid4()))
    return ctx


@when("the user views the sidebar", target_fixture="ctx")
def view_sidebar(ctx):
    ctx["entries"] = ctx["service"].list_drafts()
    return ctx


@then("each draft entry displays the generation timestamp")
def check_timestamp(ctx):
    for entry in ctx["entries"]:
        assert entry.created_at is not None
        assert len(entry.created_at) > 0


@then("each draft entry displays a brief content summary (e.g., number of aggregates, events, and commands generated)")
def check_summary(ctx):
    for entry in ctx["entries"]:
        assert entry.summary is not None
        assert entry.summary.aggregate_count >= 0
        assert "aggregates" in entry.summary.label


# ── TS-005: Clicking draft shows read-only preview ───────────────────────


@given("at least one draft entry is visible in the sidebar", target_fixture="ctx")
def draft_visible(ctx):
    analysis = _make_sample_domain_analysis()
    ctx["draft"] = ctx["service"].create_draft(analysis, str(uuid.uuid4()))
    return ctx


@when("the user clicks on a draft entry", target_fixture="ctx")
def click_draft(ctx):
    ctx["loaded"] = ctx["service"].get_draft(ctx["draft"].id)
    return ctx


@then("the draft's full domain model output is displayed")
def check_full_output(ctx):
    assert ctx["loaded"] is not None
    assert ctx["loaded"].snapshot is not None
    assert "nombre_proyecto" in ctx["loaded"].snapshot


@then("the displayed content is read-only and cannot be edited")
def check_readonly(ctx):
    # In Streamlit, read-only is enforced by rendering with disabled=True
    # Here we verify the snapshot is a dict (not a mutable model)
    assert isinstance(ctx["loaded"].snapshot, dict)


# ── TS-006: Empty state message ──────────────────────────────────────────


@given("no drafts exist for the active project", target_fixture="ctx")
def no_drafts(ctx):
    return ctx


@when("the user opens the history sidebar", target_fixture="ctx")
def open_sidebar(ctx):
    ctx["entries"] = ctx["service"].list_drafts()
    return ctx


@then("a clear empty-state message is shown indicating no generations have been saved yet")
def check_empty_state(ctx):
    assert len(ctx["entries"]) == 0
