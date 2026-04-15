"""BDD step definitions for draft-repository-contract.feature.

[TS-016, TS-017, TS-018, TS-019, TS-020, TS-021]
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from domain.models.draft import Draft, DraftSummary
from infra.adapters.file_draft_repository import FileDraftRepository
from pytest_bdd import given, scenarios, then, when

from tests.conftest import FEATURE_005_DIR, _make_sample_domain_analysis

scenarios(f"{FEATURE_005_DIR}/draft-repository-contract.feature")


# ── Shared context ───────────────────────────────────────────────────────


@pytest.fixture
def ctx():
    return {}


def _make_draft(project_name="TestProject", generation_id=None, created_at=None):
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


# ── Background ───────────────────────────────────────────────────────────


@given(
    "a FileDraftRepository initialised with a temporary drafts directory",
    target_fixture="ctx",
)
def repo_with_tmp_dir(tmp_path):
    drafts_dir = str(tmp_path / "drafts")
    os.makedirs(drafts_dir, exist_ok=True)
    return {"repo": FileDraftRepository(drafts_dir=drafts_dir), "dir": drafts_dir}


# ── TS-016: save() creates file and manifest entry ──────────────────────


@given("a valid Draft model", target_fixture="ctx")
def valid_draft(ctx):
    ctx["draft"] = _make_draft()
    return ctx


@when("save() is called with that draft", target_fixture="ctx")
def call_save(ctx):
    ctx["repo"].save(ctx["draft"])
    return ctx


@then('a file named "{draft.id}.json" exists in the drafts directory')
def check_draft_file_exists(ctx):
    path = os.path.join(ctx["dir"], f"{ctx['draft'].id}.json")
    assert os.path.exists(path)


@then("the manifest.json contains an entry with the matching draft id")
def check_manifest_entry(ctx):
    manifest_path = os.path.join(ctx["dir"], "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)
    assert any(e["id"] == ctx["draft"].id for e in manifest["entries"])


@then("the manifest entry summary matches the draft summary")
def check_manifest_summary(ctx):
    manifest_path = os.path.join(ctx["dir"], "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)
    entry = next(e for e in manifest["entries"] if e["id"] == ctx["draft"].id)
    assert entry["summary"]["aggregate_count"] == ctx["draft"].summary.aggregate_count


# ── TS-017: delete() removes file and manifest ──────────────────────────


@given("a draft has been saved via save()", target_fixture="ctx")
def saved_draft(ctx):
    ctx["draft"] = _make_draft()
    ctx["repo"].save(ctx["draft"])
    return ctx


@when("delete() is called with the draft id", target_fixture="ctx")
def call_delete(ctx):
    ctx["result"] = ctx["repo"].delete(ctx["draft"].id)
    return ctx


@then("the return value is True")
def check_true(ctx):
    assert ctx["result"] is True


@then('the file "{draft.id}.json" no longer exists in the drafts directory')
def check_file_gone(ctx):
    path = os.path.join(ctx["dir"], f"{ctx['draft'].id}.json")
    assert not os.path.exists(path)


@then("the manifest.json contains no entry for that draft id")
def check_manifest_no_entry(ctx):
    manifest_path = os.path.join(ctx["dir"], "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)
    assert not any(e["id"] == ctx["draft"].id for e in manifest["entries"])


# ── TS-018: list_entries() filters by project ────────────────────────────


@given(
    'drafts for project "Alpha" and drafts for project "Beta" have been saved',
    target_fixture="ctx",
)
def drafts_two_projects(ctx):
    now = datetime.now(timezone.utc)
    for i in range(2):
        ctx["repo"].save(_make_draft("Alpha", created_at=now + timedelta(minutes=i)))
    for i in range(2):
        ctx["repo"].save(_make_draft("Beta", created_at=now + timedelta(minutes=i)))
    return ctx


@when('list_entries(project_name="Alpha") is called', target_fixture="ctx")
def call_list_alpha(ctx):
    ctx["entries"] = ctx["repo"].list_entries(project_name="Alpha")
    return ctx


@then('only entries belonging to project "Alpha" are returned')
def check_alpha_only(ctx):
    assert all(e.project_name == "Alpha" for e in ctx["entries"])
    assert len(ctx["entries"]) == 2


@then("entries are sorted by created_at descending")
def check_sorted_desc(ctx):
    for i in range(len(ctx["entries"]) - 1):
        assert ctx["entries"][i].created_at >= ctx["entries"][i + 1].created_at


# ── TS-019: find_by_generation_id() ─────────────────────────────────────


@given(
    'a draft with generation_id "gen-123" has been saved',
    target_fixture="ctx",
)
def draft_with_gen_id(ctx):
    ctx["draft"] = _make_draft(generation_id="gen-123")
    ctx["repo"].save(ctx["draft"])
    return ctx


@when('find_by_generation_id("gen-123") is called', target_fixture="ctx")
def call_find_by_gen(ctx):
    ctx["found"] = ctx["repo"].find_by_generation_id("gen-123")
    return ctx


@then('the returned draft has generation_id "gen-123"')
def check_gen_id(ctx):
    assert ctx["found"] is not None
    assert ctx["found"].generation_id == "gen-123"


# ── TS-020: Corrupted manifest rebuilt ───────────────────────────────────


@given("draft JSON files exist in the drafts directory", target_fixture="ctx")
def draft_files_on_disk(ctx):
    ctx["draft"] = _make_draft()
    ctx["repo"].save(ctx["draft"])
    return ctx


@given("the manifest.json is corrupted or missing")
def corrupt_manifest(ctx):
    manifest_path = os.path.join(ctx["dir"], "manifest.json")
    with open(manifest_path, "w") as f:
        f.write("CORRUPTED")


@when("a new FileDraftRepository is initialised against that directory", target_fixture="ctx")
def reinit_repo(ctx):
    ctx["repo"] = FileDraftRepository(drafts_dir=ctx["dir"])
    return ctx


@then("the manifest is rebuilt from the existing draft files")
def check_rebuilt(ctx):
    entries = ctx["repo"].list_entries()
    assert len(entries) >= 1


@then("list_entries() returns all previously saved drafts")
def check_all_returned(ctx):
    entries = ctx["repo"].list_entries()
    assert any(e.id == ctx["draft"].id for e in entries)


# ── TS-021: delete() returns False for non-existent ─────────────────────


@given('no draft with id "non-existent-id" has been saved')
def no_draft_exists(ctx):
    pass


@when('delete("non-existent-id") is called', target_fixture="ctx")
def call_delete_nonexistent(ctx):
    ctx["result"] = ctx["repo"].delete("non-existent-id")
    return ctx


@then("the return value is False")
def check_false(ctx):
    assert ctx["result"] is False


@then("no error is raised")
def check_no_error(ctx):
    pass  # If we got here, no error was raised
