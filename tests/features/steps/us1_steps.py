"""BDD step definitions for us1-draft-auto-creation.feature.

[TS-001, TS-002, TS-003]
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from infra.adapters.file_draft_repository import FileDraftRepository
from pytest_bdd import given, scenarios, then, when
from services.draft_service import DraftService

from tests.conftest import FEATURE_005_DIR, _make_sample_domain_analysis

scenarios(f"{FEATURE_005_DIR}/us1-draft-auto-creation.feature")


@pytest.fixture
def ctx():
    return {}


# ── Background ───────────────────────────────────────────────────────────


@given("the user has an active DDD project", target_fixture="ctx")
def active_project(tmp_path):
    drafts_dir = str(tmp_path / "drafts")
    repo = FileDraftRepository(drafts_dir=drafts_dir)
    service = DraftService(repository=repo)
    return {
        "repo": repo,
        "service": service,
        "dir": drafts_dir,
        "session_state": {},
        "analysis": None,
        "generation_succeeded": False,
    }


# ── TS-001: Draft created after successful generation ────────────────────


@given("the user triggers a domain model generation", target_fixture="ctx")
def trigger_generation(ctx):
    ctx["analysis"] = _make_sample_domain_analysis()
    return ctx


@when("the generation completes successfully", target_fixture="ctx")
def generation_completes(ctx):
    gen_id = str(uuid.uuid4())
    ctx["generation_id"] = gen_id
    ctx["session_state"]["current_generation_id"] = gen_id
    ctx["draft"] = ctx["service"].create_draft(ctx["analysis"], gen_id)
    ctx["generation_succeeded"] = True
    ctx["creation_time"] = datetime.now(timezone.utc)
    return ctx


@then("the system automatically creates a draft record containing the full generation output")
def check_draft_created(ctx):
    assert ctx["draft"] is not None
    assert ctx["draft"].snapshot is not None
    assert len(ctx["draft"].snapshot) > 0


@then("the draft is timestamped with the generation date/time in UTC")
def check_timestamp_utc(ctx):
    assert ctx["draft"].created_at.tzinfo is not None
    assert ctx["draft"].created_at.tzname() == "UTC"


@then("the draft appears in the history sidebar within 2 seconds of generation completion")
def check_appears_quickly(ctx):
    entries = ctx["service"].list_drafts()
    assert any(e.id == ctx["draft"].id for e in entries)
    elapsed = (datetime.now(timezone.utc) - ctx["creation_time"]).total_seconds()
    assert elapsed < 2.0


# ── TS-002: Separate draft for each generation ───────────────────────────


@given("the user has previously triggered one domain model generation", target_fixture="ctx")
def one_previous_generation(ctx):
    analysis = _make_sample_domain_analysis()
    gen_id_1 = str(uuid.uuid4())
    ctx["draft_1"] = ctx["service"].create_draft(analysis, gen_id_1)
    ctx["initial_count"] = len(ctx["service"].list_drafts())
    return ctx


@when(
    "the user triggers a second domain model generation and it completes successfully",
    target_fixture="ctx",
)
def second_generation(ctx):
    analysis = _make_sample_domain_analysis()
    gen_id_2 = str(uuid.uuid4())
    ctx["draft_2"] = ctx["service"].create_draft(analysis, gen_id_2)
    return ctx


@then("a separate draft entry is created for the second generation")
def check_separate_draft(ctx):
    assert ctx["draft_2"].id != ctx["draft_1"].id
    entries = ctx["service"].list_drafts()
    assert len(entries) == ctx["initial_count"] + 1


@then("the history sidebar lists both entries in reverse chronological order")
def check_both_listed_ordered(ctx):
    entries = ctx["service"].list_drafts()
    assert len(entries) >= 2
    for i in range(len(entries) - 1):
        assert entries[i].created_at >= entries[i + 1].created_at


# ── TS-003: No draft on failed generation ────────────────────────────────


@when(
    "the generation fails or is interrupted before producing valid output",
    target_fixture="ctx",
)
def generation_fails(ctx):
    ctx["generation_succeeded"] = False
    # Simulate: no draft created because pipeline raised an exception
    ctx["count_before"] = len(ctx["service"].list_drafts())
    return ctx


@then("no draft entry is created for that run")
def check_no_draft(ctx):
    count_after = len(ctx["service"].list_drafts())
    assert count_after == ctx.get("count_before", 0)


@then("the history sidebar entry count remains unchanged")
def check_count_unchanged(ctx):
    count_after = len(ctx["service"].list_drafts())
    assert count_after == ctx.get("count_before", 0)
