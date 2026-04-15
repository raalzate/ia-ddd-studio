"""Structured event models for observable agent execution.

ProgressEvent and ErrorEvent provide an auditable trace of pipeline execution.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ProgressEvent(BaseModel):
    """Structured progress event emitted during pipeline execution."""

    checkpoint: str = Field(..., description="e.g. transcription_start, analysis_complete")
    node_name: str = Field(..., description="Originating node")
    message: str = Field(..., description="User-facing status message")
    percentage: float | None = Field(default=None, description="Optional 0.0-1.0 progress")
    timestamp: datetime = Field(default_factory=datetime.now, description="Auto-generated")


class ErrorEvent(BaseModel):
    """Structured error event emitted when a node encounters a failure."""

    node_name: str = Field(..., description="Originating node")
    error_type: str = Field(..., description="Category: validation, service, timeout, etc.")
    message: str = Field(..., description="User-readable error description")
    recoverable: bool = Field(..., description="Whether the pipeline can continue")
    timestamp: datetime = Field(default_factory=datetime.now, description="Auto-generated")
