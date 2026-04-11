"""BDD step definitions for draft-persistence.feature.

[TS-014, TS-015]
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pytest_bdd import given, scenarios, then, when

from domain.models.draft import Draft, DraftSummary
from infra.adapters.file_draft_repository import FileDraftRepository
from tests.conftest import FEATURE_005_DIR, _make_sample_domain_analysis

scenarios(f"{FEATURE_005_DIR}/draft-persistence.feature")


@pytest.fixture
def ctx():
    return {}


def _make_draft(project_name="TestProject"):
    now = datetime.now(timezone.utc)
    return Draft(
        id=str(uuid.uuid4()),
        project_name=project_name,
        generation_id=str(uuid.uuid4()),
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


# ── TS-014: Drafts survive application restart ──────────────────────────


@given("one or more draft records exist for the active project", target_fixture="ctx")
def drafts_exist(tmp_path):
    drafts_dir = str(tmp_path / "drafts")
    repo = FileDraftRepository(drafts_dir=drafts_dir)
    draft = _make_draft()
    repo.save(draft)
    return {"dir": drafts_dir, "draft": draft}


@when("the application is closed and reopened", target_fixture="ctx")
def restart_app(ctx):
    # Simulate restart by creating a new repo instance against same directory
    ctx["repo2"] = FileDraftRepository(drafts_dir=ctx["dir"])
    return ctx


@then("all draft records that existed before closing are present in the history sidebar")
def check_drafts_present(ctx):
    entries = ctx["repo2"].list_entries()
    assert any(e.id == ctx["draft"].id for e in entries)


@then("the content and timestamps of each draft are unchanged")
def check_content_unchanged(ctx):
    loaded = ctx["repo2"].load(ctx["draft"].id)
    assert loaded is not None
    assert loaded.created_at == ctx["draft"].created_at
    assert loaded.snapshot == ctx["draft"].snapshot


# ── TS-015: Drafts scoped to active project ──────────────────────────────


@given('draft records exist for project "Project A"', target_fixture="ctx")
def drafts_project_a(tmp_path):
    drafts_dir = str(tmp_path / "drafts")
    repo = FileDraftRepository(drafts_dir=drafts_dir)
    draft_a = _make_draft("Project A")
    repo.save(draft_a)
    return {"dir": drafts_dir, "repo": repo, "draft_a": draft_a}


@given('draft records exist for project "Project B"')
def drafts_project_b(ctx):
    draft_b = _make_draft("Project B")
    ctx["repo"].save(draft_b)
    ctx["draft_b"] = draft_b


@when('the user opens the history sidebar in the context of "Project A"', target_fixture="ctx")
def open_sidebar_project_a(ctx):
    ctx["entries"] = ctx["repo"].list_entries(project_name="Project A")
    return ctx


@then('only drafts belonging to "Project A" are displayed')
def check_only_a(ctx):
    assert all(e.project_name == "Project A" for e in ctx["entries"])
    assert len(ctx["entries"]) >= 1


@then('drafts from "Project B" are not visible')
def check_no_b(ctx):
    assert not any(e.project_name == "Project B" for e in ctx["entries"])
