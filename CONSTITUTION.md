<!-- SYNC IMPACT REPORT
Version: 1.0.1 (2026-04-15) — reality-alignment patch
Modified Principles:
  - IV "AI Output Must Be Auditable" — wording aligned with the actual
    enforcement mechanisms shipped in code (event emitter, `integrity_validator`
    warnings, analysis caching by hash, greedy decoding).
Added Sections: N/A
Removed Sections: N/A
Rationale for PATCH bump: principle intents are unchanged; text clarifies how
each principle is enforced in the current codebase (no new/removed principle,
no scope change).
Follow-up TODOs:
  - Add performance quality thresholds once a baseline is measured.
  - Restore .feature coverage under specs/ or retire the dormant BDD harness.
-->

# DDD Studio Constitution

## Core Principles

### I. Specification-First Development

Every feature begins with a written specification before any code is produced. No implementation
work may start without an approved `spec.md`, `plan.md`, and `tasks.md` in place.

**Rationale**: Domain modeling errors discovered late (in code) are exponentially more expensive
to fix than those caught during specification. DDD Studio's own development must model the
discipline it teaches.

### II. Domain Model Integrity

The domain model produced by DDD Studio must remain internally consistent at all times. Any
feature that writes, reads, or transforms domain elements (Actors, Commands, Events, Policies,
Aggregates, Read Models) must preserve referential integrity across the graph and enforce DDD
semantic rules. Violations discovered post-extraction (commands without an executor, events
without a producer, empty aggregates) must be surfaced as warnings through the event emitter,
not silently dropped. IDs must be canonicalised and deduplicated before the model reaches the
UI or the draft repository.

**Rationale**: DDD Studio is trusted by architects to produce valid domain models. A tool that
generates inconsistent output undermines the entire purpose of the product.

### III. Test-First (NON-NEGOTIABLE)

All new behaviors must be expressed as failing tests before production code is written.
The red-green-refactor cycle is mandatory. Tests must be reviewed and approved by the author
before implementation begins. Unit tests live under `tests/unit/` and must stay green on every
push; AI-dependent integration tests under `tests/ai/` are opt-in (require `GOOGLE_API_KEY`).

**Rationale**: Automated test coverage is the primary safety net for a system that applies
LLM inference to produce structured domain models. Without test-first discipline, regressions
in domain extraction logic will go undetected.

### IV. AI Output Must Be Auditable

Every output produced by an AI component (graph generation, inconsistency detection, element
extraction, chat-agent mutations) must be traceable to its source input. This is enforced in
code, not left to good intentions:

- Inference runs greedy decoding (hardcoded in `gemini_inference.py` and
  `gemini_chat_agent.py`) — no user-tunable temperature.
- Every analysis is keyed by `(transcript, model_name)` hash in
  `analysis_cache.py`; the same input must yield the same cached output.
- Structural warnings emitted by `integrity_validator` must flow through the
  event emitter so the UI can surface them next to the graph.
- Chat-agent tool executions must be rendered in the UI with the operation name
  and the elements affected; silent mutations are prohibited.

**Rationale**: Architects relying on DDD Studio must be able to validate and override AI
suggestions. Black-box AI outputs that cannot be inspected or challenged violate user trust
and professional standards.

### V. Iterative Refinement Over Big-Bang Delivery

Features are delivered in vertical slices that provide end-to-end value. Each slice must be
deployable and testable in isolation. Large batches of untested functionality must not be
merged into the main branch.

**Rationale**: DDD itself is an iterative practice. The tool must embody the same discipline:
incremental model refinement over large, risky releases.

## Quality Standards

- All code changes must be covered by automated tests before merging; CI runs
  `uv run pytest tests/unit/` and `uv run ruff check .` / `ruff format --check .`.
- Domain extraction accuracy must be validated against reference inputs maintained in
  the test suite (see `tests/ai/` for LLM-backed prompt regression tests).
- Any AI-assisted feature must include at least one integration test exercising the full
  input-to-graph pipeline.
- Graph mutations must preserve structural validity — no dangling edges, no duplicate
  node IDs, no empty aggregates reaching the draft repository.
- Public APIs (ports in `domain/ports.py`) must be documented with contract examples
  before implementation; port conformance is asserted in `tests/contract/`.

## Development Workflow

- **Branch strategy**: feature branches from `main`; no direct commits to `main`.
- **Code review**: at least one peer review required before merging any feature branch.
- **Quality gate**: all automated tests must pass; no linting errors; no remaining
  placeholder tokens in spec artifacts.
- **Specification gate**: `spec.md` and `plan.md` must be present and complete before a
  pull request may be opened for a new feature.
- **Definition of Done**: feature branch merged, tests green, documentation updated,
  dashboard refreshed.

## Governance

This Constitution supersedes all other development guidelines within the DDD Studio project.
Any practice that conflicts with these principles must be updated or removed.

**Amendment procedure**:
1. Propose a change with written rationale.
2. Obtain explicit approval from the project owner.
3. Increment the version (MAJOR: principle removal/redefinition; MINOR: new principle;
   PATCH: clarification only).
4. Update `LAST_AMENDED_DATE` and document the change in the Sync Impact Report.

**Compliance**: All pull requests must be reviewed for constitution compliance. Any violation
found during review blocks merge until resolved. Exceptions require documented justification
and explicit owner approval.

**Version**: 1.0.1 | **Ratified**: 2026-03-18 | **Last Amended**: 2026-04-15
