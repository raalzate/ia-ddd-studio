"""Port interfaces (Protocols) for dependency injection.

Defines InferencePort, TranscriptionPort, CachePort, EventEmitter,
ChatAgentPort, and DraftRepositoryPort as Protocol classes.
Infrastructure adapters implement these.
"""

from __future__ import annotations

from typing import Any, Protocol, TypeVar, runtime_checkable

from domain.events import ErrorEvent, ProgressEvent
from domain.models.draft import Draft, DraftManifestEntry

T = TypeVar("T")


@runtime_checkable
class InferencePort(Protocol):
    """Port for AI inference operations."""

    def invoke(self, prompt: str, output_schema: type[T]) -> T:
        """Send prompt to AI service and return structured output."""
        ...

    def invoke_text(self, prompt: str) -> str:
        """Send prompt and return raw text response."""
        ...


@runtime_checkable
class TranscriptionPort(Protocol):
    """Port for audio-to-text transcription."""

    def transcribe(self, audio_bytes: bytes, language: str = "es") -> str:
        """Convert audio bytes to text."""
        ...


@runtime_checkable
class CachePort(Protocol):
    """Port for transcription caching."""

    def get(self, key: str) -> str | None:
        """Retrieve cached transcription by key."""
        ...

    def set(self, key: str, value: str) -> None:
        """Store transcription in cache."""
        ...


@runtime_checkable
class EventEmitter(Protocol):
    """Port for emitting structured pipeline events."""

    def __call__(self, event: ProgressEvent | ErrorEvent) -> None:
        """Emit a structured event."""
        ...


@runtime_checkable
class ChatAgentPort(Protocol):
    """Port for the tool-calling chat agent."""

    def run(
        self,
        user_message: str,
        history: list[dict[str, str]],
        system_prompt: str,
        model_accessor: Any,
    ) -> Any:
        """Execute one agent turn: send user message, handle tool calls, return final response."""
        ...


@runtime_checkable
class DraftRepositoryPort(Protocol):
    """Port for draft persistence operations."""

    def save(self, draft: Draft) -> None:
        """Persist a draft record (create or update)."""
        ...

    def load(self, draft_id: str) -> Draft | None:
        """Load a full draft by ID."""
        ...

    def delete(self, draft_id: str) -> bool:
        """Delete a draft permanently. Returns True if deleted, False if not found."""
        ...

    def list_entries(self, project_name: str | None = None) -> list[DraftManifestEntry]:
        """List all draft entries, optionally filtered by project. Sorted by created_at desc."""
        ...

    def find_by_generation_id(self, generation_id: str) -> Draft | None:
        """Find a draft by its generation_id."""
        ...
