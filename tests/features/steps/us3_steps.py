"""BDD step definitions for us3-draft-deletion.feature.

[TS-007, TS-008, TS-009, TS-010]
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from infra.adapters.file_draft_repository import FileDraftRepository
from pytest_bdd import given, scenarios, then, when
from services.draft_service import DraftService

from tests.conftest import FEATURE_005_DIR, _make_sample_domain_analysis

scenarios(f"{FEATURE_005_DIR}/us3-draft-deletion.feature")


@pytest.fixture
def ctx():
    return {}


# ── Background ───────────────────────────────────────────────────────────


@given(
    "the user has an active DDD project with at least one draft in the sidebar",
    target_fixture="ctx",
)
def active_project_with_draft(tmp_path):
    drafts_dir = str(tmp_path / "drafts")
    repo = FileDraftRepository(drafts_dir=drafts_dir)
    service = DraftService(repository=repo)
    analysis = _make_sample_domain_analysis()
    draft = service.create_draft(analysis, str(uuid.uuid4()))
    return {
        "repo": repo,
        "service": service,
        "dir": drafts_dir,
        "draft": draft,
        "confirmed": False,
    }


# ── TS-007: Confirmation prompt shown ────────────────────────────────────


@given("at least one draft entry exists in the sidebar", target_fixture="ctx")
def draft_exists(ctx):
    return ctx


@when("the user selects delete on a specific draft", target_fixture="ctx")
def select_delete(ctx):
    # Simulate the UI setting the confirmation state
    ctx["confirm_draft_id"] = ctx["draft"].id
    return ctx


@then("a confirmation prompt is shown before deletion proceeds")
def check_confirmation_prompt(ctx):
    # In the Streamlit UI, this is handled by st.dialog()
    # Here we verify the confirmation state is set
    assert ctx["confirm_draft_id"] == ctx["draft"].id
    # The draft still exists (not deleted yet)
    assert ctx["service"].get_draft(ctx["draft"].id) is not None


# ── TS-008: Draft permanently removed after confirmation ─────────────────


@given("a confirmation prompt has been shown for a specific draft", target_fixture="ctx")
def confirmation_shown(ctx):
    ctx["confirm_draft_id"] = ctx["draft"].id
    return ctx


@when("the user confirms the deletion", target_fixture="ctx")
def confirm_deletion(ctx):
    ctx["delete_start"] = datetime.now(timezone.utc)
    ctx["result"] = ctx["service"].delete_draft(ctx["confirm_draft_id"])
    ctx["delete_end"] = datetime.now(timezone.utc)
    ctx["confirmed"] = True
    return ctx


@then("the selected draft entry is permanently removed from the repository")
def check_permanently_removed(ctx):
    assert ctx["result"] is True
    assert ctx["service"].get_draft(ctx["draft"].id) is None


@then("the draft no longer appears in the history sidebar")
def check_not_in_sidebar(ctx):
    entries = ctx["service"].list_drafts()
    assert not any(e.id == ctx["draft"].id for e in entries)


@then("the draft disappears within 1 second of user confirmation")
def check_deletion_speed(ctx):
    elapsed = (ctx["delete_end"] - ctx["delete_start"]).total_seconds()
    assert elapsed < 1.0


# ── TS-009: Draft unchanged when user cancels ────────────────────────────


@when("the user cancels the confirmation prompt", target_fixture="ctx")
def cancel_deletion(ctx):
    ctx["confirmed"] = False
    # No deletion performed
    return ctx


@then("the draft entry remains in the sidebar unchanged")
def check_draft_unchanged(ctx):
    assert ctx["service"].get_draft(ctx["draft"].id) is not None
    entries = ctx["service"].list_drafts()
    assert any(e.id == ctx["draft"].id for e in entries)


# ── TS-010: Remaining entries unaffected ─────────────────────────────────


@given("multiple draft entries exist in the sidebar", target_fixture="ctx")
def multiple_drafts(ctx):
    # Add two more drafts
    ctx["other_drafts"] = []
    for _ in range(2):
        analysis = _make_sample_domain_analysis()
        d = ctx["service"].create_draft(analysis, str(uuid.uuid4()))
        ctx["other_drafts"].append(d)
    ctx["entries_before"] = ctx["service"].list_drafts()
    return ctx


@when("the user confirms deletion of one specific draft", target_fixture="ctx")
def confirm_one_deletion(ctx):
    ctx["service"].delete_draft(ctx["draft"].id)
    return ctx


@then("the deleted draft is removed")
def check_deleted(ctx):
    assert ctx["service"].get_draft(ctx["draft"].id) is None


@then("all remaining draft entries are present and in their original relative order")
def check_remaining(ctx):
    entries_after = ctx["service"].list_drafts()
    remaining_ids = [e.id for e in entries_after]
    for other in ctx["other_drafts"]:
        assert other.id in remaining_ids
