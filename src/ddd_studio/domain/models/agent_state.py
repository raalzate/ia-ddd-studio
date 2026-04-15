"""AgentState Pydantic model and NodeContract dataclass.

Defines the typed state schema exchanged between agent nodes in the LangGraph pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from models.domain_analysis import DomainAnalysis
from pydantic import BaseModel, Field, model_validator


@dataclass
class NodeContract:
    """Declares the input/output contract for each agent node."""

    node_name: str
    required_inputs: list[str] = field(default_factory=list)
    produced_outputs: list[str] = field(default_factory=list)
    emits_events: list[str] = field(default_factory=list)


class AgentState(BaseModel):
    """Typed state schema for the LangGraph agent pipeline.

    Replaces the previous untyped EventStormingState TypedDict.
    All fields are optional to support partial state updates (LangGraph merge semantics).
    """

    audio_path: str | None = Field(default=None, description="Path to uploaded audio file")
    audio_name: str | None = Field(default=None, description="Original filename")
    transcript: str | None = Field(default=None, description="Transcribed text")
    context: str | None = Field(default=None, description="Supplementary PDF/document context")
    analysis: DomainAnalysis | None = Field(default=None, description="Structured DomainAnalysis result")
    specs: dict | None = Field(default=None, description="Generated specification artifacts")
    has_refine: bool = Field(default=False, description="Whether refinement context was provided")
    cache_path: str | None = Field(default=None, description="Path to cached transcription")
    cache_exists: bool = Field(default=False, description="Whether cache hit occurred")
    error: str | None = Field(default=None, description="Error message if pipeline failed")

    @model_validator(mode="after")
    def refine_requires_context(self) -> AgentState:
        if self.has_refine and self.context is None:
            raise ValueError("context must not be None when has_refine is True")
        return self

    model_config = {"arbitrary_types_allowed": True}
