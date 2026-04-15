# DDD Studio Premise

## What

DDD Studio is an interactive domain analysis and Event Storming workbench for software architects
and domain experts. It combines AI-powered visual modeling with structured knowledge extraction
to design, validate, and document complex software systems using Domain-Driven Design (DDD)
principles. The application ingests audio recordings, transcriptions, and PDF documents, then
produces a canonicalized `DomainAnalysis` (Actors, Commands, Events, Policies, Aggregates,
Read Models) rendered as an interactive graph that can be refined through a conversational
Gemini-powered agent.

## Who

- **Software architects**: designing bounded contexts, aggregates, and service decompositions.
- **Domain experts**: participating in Event Storming workshops and reviewing domain models.
- **Engineering teams**: validating domain consistency before implementation begins.

## Why

Translating tacit business knowledge into precise DDD models is labor-intensive, error-prone,
and often stalls when no facilitator is available. DDD Studio automates the extraction of
domain elements (Actors, Commands, Events, Policies, Aggregates, Read Models) from unstructured
input — workshop recordings, PDFs, stakeholder interviews — validates the resulting graph
against DDD invariants, and exposes an AI "Senior Architect" agent to surface logical gaps,
missing integrations, and orphaned events, accelerating the path from discovery to a validated
domain model.

## Domain

**Domain-Driven Design (DDD) and Event Storming.** Key terms:
- **Aggregate**: cluster of domain objects treated as a unit for data changes.
- **Command**: intent to change system state (verb form, e.g., "PlaceOrder").
- **Domain Event**: fact that something occurred (past tense, e.g., "OrderPlaced").
- **Policy**: reaction rule — "whenever Event X occurs, do Command Y".
- **Read Model**: denormalized projection consumed by queries/UI.
- **Bounded Context**: explicit boundary within which a domain model applies.
- **Ubiquitous Language**: the canonical vocabulary the tool enforces across the graph.

## Scope

**In scope:**
- Audio transcription via `FasterWhisperTranscriptionAdapter` (local) or
  `GoogleTranscriptionAdapter` (remote), selected by `WHISPER_MODEL`.
- PDF/document ingestion for requirements and specification parsing.
- Single-shot LLM extraction of Event Storming elements (Actors, Commands, Events,
  Policies, Aggregates, Read Models) via Gemini.
- Structural validation of the resulting graph (`integrity_validator`) and ID
  canonicalisation / deduplication (`analysis_normalizer`).
- Deterministic caching of analyses keyed by `(transcript, model_name)` hash.
- Inter-agent workshop simulation (`WorkshopSimulator`) that synthesises
  facilitator/expert transcripts from a domain description.
- Conversational "Senior Architect" chat agent (ReAct) with tool-calling to mutate
  the graph (add/remove/rename nodes, refine aggregates) from the UI.
- Persistent generation history via `DraftService` + `FileDraftRepository`.
- Artefact export: Mermaid, PlantUML, PDF, and Gherkin-style specifications.

**Out of scope:**
- Code generation from domain models.
- Direct database schema creation or ORM mapping.
- Multi-tenant / SaaS deployment infrastructure.
- Byte-for-byte deterministic LLM output (the system promises *semantic*
  stability via greedy decoding + caching, not bit-identical responses).
