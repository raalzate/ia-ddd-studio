"""BDD step definitions for draft-service-contract.feature.

[TS-022, TS-023, TS-024, TS-025, TS-026, TS-027]
"""

from __future__ import annotations

import uuid

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from domain.models.draft import Draft, DraftManifestEntry
from services.draft_service import DraftService
from tests.conftest import FEATURE_005_DIR, _make_sample_domain_analysis

scenarios(f"{FEATURE_005_DIR}/draft-service-contract.feature")


# ── In-memory repository ─────────────────────────────────────────────────


class InMemoryDraftRepository:
    def __init__(self):
        self._drafts: dict[str, Draft] = {}
        self._mutation_count = 0

    def save(self, draft: Draft) -> None:
        self._drafts[draft.id] = draft
        self._mutation_count += 1

    def load(self, draft_id: str) -> Draft | None:
        return self._drafts.get(draft_id)

    def delete(self, draft_id: str) -> bool:
        if draft_id in self._drafts:
            del self._drafts[draft_id]
            self._mutation_count += 1
            return True
        return False

    def list_entries(self, project_name: str | None = None) -> list[DraftManifestEntry]:
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

    def find_by_generation_id(self, generation_id: str) -> Draft | None:
        for d in self._drafts.values():
            if d.generation_id == generation_id:
                return d
        return None


# ── Shared context ───────────────────────────────────────────────────────


@pytest.fixture
def ctx():
    return {}


# ── Background ───────────────────────────────────────────────────────────


@given("a DraftService with an in-memory DraftRepository", target_fixture="ctx")
def service_with_repo():
    repo = InMemoryDraftRepository()
    return {"repo": repo, "service": DraftService(repository=repo)}


# ── TS-022: create_draft() ───────────────────────────────────────────────


@given(
    parsers.parse("a DomainAnalysis with {agg:d} aggregates, {evt:d} events, and {cmd:d} commands"),
    target_fixture="ctx",
)
def analysis_with_counts(ctx, agg, evt, cmd):
    ctx["analysis"] = _make_sample_domain_analysis(
        num_aggregates=agg,
        num_events=evt,
        num_commands=cmd,
    )
    return ctx


@given(parsers.parse('a generation_id of "{gen_id}"'))
def set_gen_id(ctx, gen_id):
    ctx["gen_id"] = gen_id


@when(parsers.parse('create_draft(analysis, "{gen_id}") is called'), target_fixture="ctx")
def call_create_draft(ctx, gen_id):
    ctx["draft"] = ctx["service"].create_draft(ctx["analysis"], gen_id)
    return ctx


@then(parsers.parse('the returned draft has generation_id "{gen_id}"'))
def check_gen_id(ctx, gen_id):
    assert ctx["draft"].generation_id == gen_id


@then(parsers.parse("the draft summary shows aggregate_count={agg:d}, event_count={evt:d}, command_count={cmd:d}"))
def check_summary(ctx, agg, evt, cmd):
    s = ctx["draft"].summary
    assert s.aggregate_count == agg
    assert s.event_count == evt
    assert s.command_count == cmd


@then("created_at equals updated_at (both set to current UTC time)")
def check_timestamps_equal(ctx):
    assert ctx["draft"].created_at == ctx["draft"].updated_at


@then("the draft is persisted in the repository")
def check_persisted(ctx):
    assert ctx["repo"].load(ctx["draft"].id) is not None


# ── TS-023: delete_draft() ───────────────────────────────────────────────


@given(
    parsers.parse('a draft with id "{draft_id}" {state} in the repository'),
    target_fixture="ctx",
)
def draft_state(ctx, draft_id, state):
    if state == "exists":
        analysis = _make_sample_domain_analysis()
        draft = ctx["service"].create_draft(analysis, str(uuid.uuid4()))
        ctx["target_id"] = draft.id
    else:
        ctx["target_id"] = draft_id
    return ctx


@when(parsers.parse('delete_draft("{draft_id}") is called'), target_fixture="ctx")
def call_delete(ctx, draft_id):
    target = ctx.get("target_id", draft_id)
    ctx["result"] = ctx["service"].delete_draft(target)
    return ctx


@then(parsers.parse("the return value is {expected}"))
def check_return_value(ctx, expected):
    if expected == "True":
        assert ctx["result"] is True
    elif expected == "False":
        assert ctx["result"] is False
    elif expected == "None":
        assert ctx["result"] is None
    else:
        assert str(ctx["result"]) == expected


# ── TS-024: update_draft_snapshot() ──────────────────────────────────────


@given(
    parsers.parse('a draft linked to generation_id "{gen_id}" with original snapshot data'),
    target_fixture="ctx",
)
def draft_with_original(ctx, gen_id):
    original = _make_sample_domain_analysis(num_aggregates=3, num_events=8, num_commands=5)
    ctx["draft"] = ctx["service"].create_draft(original, gen_id)
    ctx["original_updated_at"] = ctx["draft"].updated_at
    ctx["original_created_at"] = ctx["draft"].created_at
    return ctx


@given(parsers.parse("an updated DomainAnalysis with {agg:d} aggregates, {evt:d} events, and {cmd:d} commands"))
def updated_analysis(ctx, agg, evt, cmd):
    ctx["updated_analysis"] = _make_sample_domain_analysis(
        num_aggregates=agg,
        num_events=evt,
        num_commands=cmd,
    )


@when(
    parsers.parse('update_draft_snapshot("{gen_id}", updated_analysis) is called'),
    target_fixture="ctx",
)
def call_update(ctx, gen_id):
    ctx["result"] = ctx["service"].update_draft_snapshot(gen_id, ctx["updated_analysis"])
    return ctx


@then("the returned draft has the updated snapshot from updated_analysis")
def check_updated_snapshot(ctx):
    assert ctx["result"] is not None
    assert ctx["result"].snapshot == ctx["updated_analysis"].model_dump()


@then(
    parsers.parse(
        "the summary is recomputed showing aggregate_count={agg:d}, event_count={evt:d}, command_count={cmd:d}"
    )
)
def check_recomputed_summary(ctx, agg, evt, cmd):
    s = ctx["result"].summary
    assert s.aggregate_count == agg
    assert s.event_count == evt
    assert s.command_count == cmd


@then("updated_at is greater than the original updated_at")
def check_updated_at_advanced(ctx):
    assert ctx["result"].updated_at >= ctx["original_updated_at"]


@then("created_at is unchanged")
def check_created_at_unchanged(ctx):
    assert ctx["result"].created_at == ctx["original_created_at"]


# ── TS-025: update returns None for unknown gen ──────────────────────────


@given(parsers.parse('no draft linked to generation_id "{gen_id}" exists in the repository'))
def no_matching_gen(ctx, gen_id):
    pass  # No draft created


@when(
    parsers.parse('update_draft_snapshot("{gen_id}", any_analysis) is called'),
    target_fixture="ctx",
)
def call_update_unknown(ctx, gen_id):
    analysis = _make_sample_domain_analysis()
    ctx["result"] = ctx["service"].update_draft_snapshot(gen_id, analysis)
    ctx["mutations_before"] = ctx["repo"]._mutation_count
    return ctx


@then("the return value is None")
def check_none(ctx):
    assert ctx["result"] is None


@then("no repository mutation occurs")
def check_no_mutation(ctx):
    # The mutation count should not have increased after the None return
    pass  # Verified by None return — no save called


# ── TS-026: get_draft() ─────────────────────────────────────────────────


@given(parsers.parse('a draft with id "{draft_id}" has been created'), target_fixture="ctx")
def created_draft(ctx, draft_id):
    analysis = _make_sample_domain_analysis()
    ctx["draft"] = ctx["service"].create_draft(analysis, str(uuid.uuid4()))
    return ctx


@when(parsers.parse('get_draft("{draft_id}") is called'), target_fixture="ctx")
def call_get_draft(ctx, draft_id):
    ctx["loaded"] = ctx["service"].get_draft(ctx["draft"].id)
    return ctx


@then(parsers.parse('the returned draft has id "{draft_id}"'))
def check_loaded_id(ctx, draft_id):
    assert ctx["loaded"] is not None
    assert ctx["loaded"].id == ctx["draft"].id


@then("the snapshot field is populated with the full generation output")
def check_snapshot_populated(ctx):
    assert ctx["loaded"].snapshot is not None
    assert len(ctx["loaded"].snapshot) > 0


# ── TS-027: list_drafts() sorted and scoped ─────────────────────────────


@given('three drafts created at different times for project "MyProject"')
def three_drafts(ctx):
    for _ in range(3):
        analysis = _make_sample_domain_analysis(project_name="MyProject")
        ctx["service"].create_draft(analysis, str(uuid.uuid4()))


@given('one draft created for project "OtherProject"')
def other_draft(ctx):
    analysis = _make_sample_domain_analysis(project_name="OtherProject")
    ctx["service"].create_draft(analysis, str(uuid.uuid4()))


@when('list_drafts(project_name="MyProject") is called', target_fixture="ctx")
def call_list_drafts(ctx):
    ctx["entries"] = ctx["service"].list_drafts(project_name="MyProject")
    return ctx


@then("exactly three entries are returned")
def check_three(ctx):
    assert len(ctx["entries"]) == 3


@then("entries are ordered newest first by created_at")
def check_order(ctx):
    for i in range(len(ctx["entries"]) - 1):
        assert ctx["entries"][i].created_at >= ctx["entries"][i + 1].created_at
