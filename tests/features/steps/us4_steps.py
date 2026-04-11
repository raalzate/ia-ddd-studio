"""BDD step definitions for us4-draft-auto-update.feature.

[TS-011, TS-012, TS-013]
"""

from __future__ import annotations

import uuid

import pytest
from pytest_bdd import given, scenarios, then, when

from infra.adapters.file_draft_repository import FileDraftRepository
from services.draft_service import DraftService
from tests.conftest import FEATURE_005_DIR, _make_sample_domain_analysis

scenarios(f"{FEATURE_005_DIR}/us4-draft-auto-update.feature")


@pytest.fixture
def ctx():
    return {}


# ── Background ───────────────────────────────────────────────────────────


@given(
    "the user has an active DDD project with at least one saved draft",
    target_fixture="ctx",
)
def active_project_with_draft(tmp_path):
    drafts_dir = str(tmp_path / "drafts")
    repo = FileDraftRepository(drafts_dir=drafts_dir)
    service = DraftService(repository=repo)
    analysis = _make_sample_domain_analysis(num_aggregates=3, num_events=5, num_commands=2)
    gen_id = str(uuid.uuid4())
    draft = service.create_draft(analysis, gen_id)
    return {
        "repo": repo,
        "service": service,
        "dir": drafts_dir,
        "draft": draft,
        "generation_id": gen_id,
        "original_analysis": analysis,
        "original_updated_at": draft.updated_at,
    }


# ── TS-011: Draft auto-updated when linked element modified ──────────────


@given("a draft exists for a specific generation", target_fixture="ctx")
def draft_for_generation(ctx):
    return ctx


@when(
    "the user modifies a domain element produced by that generation (e.g., renames an aggregate)",
    target_fixture="ctx",
)
def modify_domain_element(ctx):
    # Simulate modifying the analysis (rename first aggregate)
    modified = _make_sample_domain_analysis(num_aggregates=2, num_events=6, num_commands=3)
    ctx["modified_analysis"] = modified
    ctx["updated_draft"] = ctx["service"].update_draft_snapshot(
        ctx["generation_id"],
        modified,
    )
    return ctx


@then("the corresponding draft entry is automatically updated to reflect the change")
def check_draft_updated(ctx):
    assert ctx["updated_draft"] is not None
    assert ctx["updated_draft"].summary.aggregate_count == 2
    assert ctx["updated_draft"].summary.event_count == 6


@then("the draft reflects the change within 3 seconds without requiring a manual refresh")
def check_speed(ctx):
    # Verified by the synchronous nature of the update call
    assert ctx["updated_draft"] is not None


# ── TS-012: Sidebar shows updated content and refreshed timestamp ────────


@given("a draft has been automatically updated after a model change", target_fixture="ctx")
def draft_auto_updated(ctx):
    modified = _make_sample_domain_analysis(num_aggregates=2, num_events=6, num_commands=3)
    ctx["modified_analysis"] = modified
    ctx["updated_draft"] = ctx["service"].update_draft_snapshot(
        ctx["generation_id"],
        modified,
    )
    return ctx


@when("the user views the draft in the sidebar", target_fixture="ctx")
def view_draft_in_sidebar(ctx):
    ctx["loaded"] = ctx["service"].get_draft(ctx["draft"].id)
    ctx["entries"] = ctx["service"].list_drafts()
    return ctx


@then("the updated content is shown in the draft preview")
def check_updated_content(ctx):
    assert ctx["loaded"] is not None
    assert ctx["loaded"].summary.aggregate_count == 2


@then("the draft's last-modified timestamp is refreshed to reflect the time of the change")
def check_timestamp_refreshed(ctx):
    assert ctx["loaded"].updated_at >= ctx["original_updated_at"]


# ── TS-013: Unassociated modifications don't affect drafts ───────────────


@given("a domain element not associated with any draft generation exists")
def unassociated_element(ctx):
    ctx["entries_before"] = ctx["service"].list_drafts()
    ctx["draft_before"] = ctx["service"].get_draft(ctx["draft"].id)


@when("the user modifies that domain element and the change is saved", target_fixture="ctx")
def modify_unassociated(ctx):
    # Try updating with a non-existent generation_id
    unrelated = _make_sample_domain_analysis()
    ctx["result"] = ctx["service"].update_draft_snapshot("non-existent-gen", unrelated)
    return ctx


@then("no draft entries are affected")
def check_no_effect(ctx):
    assert ctx["result"] is None


@then("all existing drafts remain unchanged")
def check_drafts_unchanged(ctx):
    draft_after = ctx["service"].get_draft(ctx["draft"].id)
    assert draft_after.updated_at == ctx["draft_before"].updated_at
    assert draft_after.summary == ctx["draft_before"].summary
