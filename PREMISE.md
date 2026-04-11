# DDD Studio Premise

## What

DDD Studio is an interactive domain analysis and Event Storming workbench for software architects
and domain experts. It combines AI-powered visual modeling with structured knowledge extraction
to design, validate, and document complex software systems using Domain-Driven Design (DDD)
principles. The application ingests audio recordings, transcriptions, and documents, then
automatically extracts domain elements and renders them as interactive, editable graphs.

## Who

- **Software architects**: designing bounded contexts, aggregates, and service decompositions.
- **Domain experts**: participating in Event Storming workshops and reviewing domain models.
- **Engineering teams**: validating domain consistency before implementation begins.

## Why

Translating tacit business knowledge into precise DDD models is labor-intensive, error-prone,
and often stalls when no facilitator is available. DDD Studio automates the extraction of
domain elements (Commands, Events, Aggregates, Policies) from unstructured input — workshop
recordings, PDFs, stakeholder interviews — and applies an AI "Senior Architect" agent to
surface logical gaps, missing integrations, and orphaned events, accelerating the path from
discovery to a validated domain model.

## Domain

**Domain-Driven Design (DDD) and Event Storming.** Key terms:
- **Aggregate**: cluster of domain objects treated as a unit for data changes.
- **Command**: intent to change system state (verb form, e.g., "PlaceOrder").
- **Domain Event**: fact that something occurred (past tense, e.g., "OrderPlaced").
- **Policy**: reaction rule — "whenever Event X occurs, do Command Y".
- **Bounded Context**: explicit boundary within which a domain model applies.
- **TOON Format**: compressed context representation for efficient LLM consumption.

## Scope

**In scope:**
- Audio transcription and NLP-based domain element extraction (via Whisper + LLM).
- PDF/document ingestion for requirements and specification parsing.
- Automated generation of Event Storming graphs (nodes: Commands, Events, Aggregates, Policies).
- AI "Senior Architect" chat agent for domain inconsistency analysis.
- Live graph editing (nodes and edges) in the UI.
- Structural analysis (complexity, coupling, cohesion metrics).

**Out of scope:**
- Code generation from domain models.
- Direct database schema creation or ORM mapping.
- Multi-tenant / SaaS deployment infrastructure.
