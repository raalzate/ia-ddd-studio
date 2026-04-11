from typing import TypedDict

from .domain_analysis import DomainAnalysis


class EventStormingState(TypedDict):
    audio_path: str
    has_refine: bool | None
    context: str | None
    audio_name: str
    cache_path: str
    cache_existe: bool
    transcription: str | None
    analysis: DomainAnalysis | None
    error: str | None
    logs: str | None
    status: str
    transcript: str
    specs: dict[str, str] | None
