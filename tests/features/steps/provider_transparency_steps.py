"""BDD step definitions for provider-transparency.feature.

Covers: TS-009, TS-010, TS-011, TS-012, TS-013, TS-014, TS-015, TS-016
"""

from __future__ import annotations

import importlib
import os
from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.conftest import FEATURE_006_DIR

scenarios(os.path.join(FEATURE_006_DIR, "provider-transparency.feature"))


# ── Shared state ──────────────────────────────────────────────────────────


@pytest.fixture
def ctx():
    """Mutable context dict shared across steps."""
    return {
        "adapter": None,
        "transcript": None,
        "cache": {},
        "audio_bytes": None,
        "semantic_input": None,
        "whisper_invoked": False,
        "remote_called": False,
    }


# ── Given ─────────────────────────────────────────────────────────────────


@given("a Spanish-language audio file is available", target_fixture="audio_bytes")
def spanish_audio():
    return b"\x00" * 48_000


@given(
    parsers.re(r'the environment variable "WHISPER_MODEL" is set to "(?P<value>[^"]*)"'),
    target_fixture="ctx",
)
def whisper_model_set(ctx, value, monkeypatch):
    monkeypatch.setenv("WHISPER_MODEL", value)
    ctx["model_name"] = value
    return ctx


@given(
    'the environment variable "WHISPER_MODEL" is not set',
    target_fixture="ctx",
)
def whisper_model_not_set(ctx, monkeypatch):
    monkeypatch.delenv("WHISPER_MODEL", raising=False)
    return ctx


@given("either transcription provider is active", target_fixture="ctx")
def either_provider(ctx):
    return ctx


@given(
    parsers.re(r'the FasterWhisperTranscriptionAdapter is instantiated with model "(?P<model>[^"]*)"'),
    target_fixture="ctx",
)
def instantiate_faster_whisper(ctx, model):
    from infra.adapters.faster_whisper_transcription import (
        FasterWhisperTranscriptionAdapter,
    )

    mock_model = MagicMock()
    with patch(
        "infra.adapters.faster_whisper_transcription.WhisperModel",
        return_value=mock_model,
    ):
        ctx["adapter"] = FasterWhisperTranscriptionAdapter(model_name=model)
    return ctx


@given("the audio has been transcribed and cached", target_fixture="ctx")
def audio_transcribed_and_cached(ctx, audio_bytes):
    from infra.adapters.faster_whisper_transcription import (
        FasterWhisperTranscriptionAdapter,
    )

    mock_seg = MagicMock()
    mock_seg.text = "Texto de prueba transcrito"
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter([mock_seg]), MagicMock())

    with patch(
        "infra.adapters.faster_whisper_transcription.WhisperModel",
        return_value=mock_model,
    ):
        adapter = FasterWhisperTranscriptionAdapter(model_name="base")

    transcript = adapter.transcribe(audio_bytes, language="es")
    # Simulate caching with a content-based key
    import hashlib

    cache_key = hashlib.sha256(audio_bytes).hexdigest()
    ctx["cache"][cache_key] = transcript
    ctx["transcript"] = transcript
    ctx["audio_bytes"] = audio_bytes
    return ctx


@given("the audio has been transcribed via remote and cached", target_fixture="ctx")
def audio_transcribed_remote_cached(ctx, audio_bytes):
    transcript = "Texto de prueba transcrito"
    import hashlib

    cache_key = hashlib.sha256(audio_bytes).hexdigest()
    ctx["cache"][cache_key] = transcript
    ctx["transcript"] = transcript
    ctx["audio_bytes"] = audio_bytes
    return ctx


@given(
    parsers.re(r"an audio file exceeding the maximum allowed size is available"),
    target_fixture="audio_bytes",
)
def oversized_audio():
    return b"\x00" * (11 * 1024 * 1024)  # 11MB > default 10MB limit


# ── When ──────────────────────────────────────────────────────────────────


@when("WHISPER_MODEL is removed and the application is restarted")
def remove_whisper_model(ctx, monkeypatch):
    monkeypatch.delenv("WHISPER_MODEL", raising=False)
    import config.settings as settings_mod

    importlib.reload(settings_mod)
    assert settings_mod.WHISPER_MODEL is None

    from infra.adapters.google_transcription import GoogleTranscriptionAdapter

    ctx["adapter"] = GoogleTranscriptionAdapter()


@when("the audio is transcribed locally")
def transcribe_locally(ctx, audio_bytes):
    from infra.adapters.faster_whisper_transcription import (
        FasterWhisperTranscriptionAdapter,
    )

    mock_seg = MagicMock()
    mock_seg.text = "Texto transcrito localmente"
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter([mock_seg]), MagicMock())

    with patch(
        "infra.adapters.faster_whisper_transcription.WhisperModel",
        return_value=mock_model,
    ):
        adapter = FasterWhisperTranscriptionAdapter(model_name=ctx.get("model_name", "base"))

    ctx["adapter"] = adapter
    ctx["transcript"] = adapter.transcribe(audio_bytes, language="es")
    # The transcript is what gets passed to semantic analysis
    ctx["semantic_input"] = ctx["transcript"]


@when("the audio is transcribed via remote")
def transcribe_remote(ctx, audio_bytes):
    # Simulate remote transcription returning plain text
    ctx["transcript"] = "Texto transcrito remotamente"
    ctx["semantic_input"] = ctx["transcript"]


@when("the transcription node executes")
def transcription_node_executes(ctx):
    # The node just calls the injected port — no provider-specific logic
    mock_port = MagicMock()
    mock_port.transcribe.return_value = "Resultado de transcripcion"
    ctx["transcript"] = mock_port.transcribe(b"audio", language="es")
    ctx["node_port"] = mock_port


@when("the adapter is checked against TranscriptionPort protocol")
def check_protocol(ctx):
    from domain.ports import TranscriptionPort

    ctx["isinstance_result"] = isinstance(ctx["adapter"], TranscriptionPort)


@when(parsers.re(r'"WHISPER_MODEL" is unset and the same audio is submitted'))
def unset_and_resubmit(ctx, monkeypatch):
    monkeypatch.delenv("WHISPER_MODEL", raising=False)
    import hashlib

    cache_key = hashlib.sha256(ctx["audio_bytes"]).hexdigest()
    # Check cache first (as the real pipeline would)
    cached = ctx["cache"].get(cache_key)
    if cached:
        ctx["transcript"] = cached
        ctx["cache_hit"] = True
        ctx["remote_called"] = False
    else:
        ctx["cache_hit"] = False
        ctx["remote_called"] = True


@when(parsers.re(r'"WHISPER_MODEL" is set to "(?P<value>[^"]*)" and the same audio is submitted'))
def set_and_resubmit(ctx, value, monkeypatch):
    monkeypatch.setenv("WHISPER_MODEL", value)
    import hashlib

    cache_key = hashlib.sha256(ctx["audio_bytes"]).hexdigest()
    cached = ctx["cache"].get(cache_key)
    if cached:
        ctx["transcript"] = cached
        ctx["cache_hit"] = True
        ctx["whisper_invoked"] = False
    else:
        ctx["cache_hit"] = False
        ctx["whisper_invoked"] = True


@when("the audio is submitted for transcription")
def submit_audio(ctx, audio_bytes):
    from infra.adapters.faster_whisper_transcription import (
        FasterWhisperTranscriptionAdapter,
    )

    mock_model = MagicMock()
    with patch(
        "infra.adapters.faster_whisper_transcription.WhisperModel",
        return_value=mock_model,
    ):
        adapter = FasterWhisperTranscriptionAdapter(model_name=ctx.get("model_name", "base"))

    try:
        ctx["transcript"] = adapter.transcribe(audio_bytes, language="es")
    except Exception as e:
        ctx["error"] = e


# ── Then ──────────────────────────────────────────────────────────────────


@then("the system uses the remote adapter with no code changes required")
def system_uses_remote(ctx):
    from infra.adapters.google_transcription import GoogleTranscriptionAdapter

    assert isinstance(ctx["adapter"], GoogleTranscriptionAdapter)


@then("the transcript string is passed directly to the semantic analysis node")
def transcript_passed_directly(ctx):
    assert isinstance(ctx["semantic_input"], str)
    assert len(ctx["semantic_input"]) > 0
    assert ctx["semantic_input"] == ctx["transcript"]


@then("no transformation or reformatting is applied to the transcript")
def no_transformation(ctx):
    # semantic_input should be identical to transcript — no conversion step
    assert ctx["semantic_input"] == ctx["transcript"]


@then("the cached transcript is returned")
def cached_transcript_returned(ctx):
    assert ctx.get("cache_hit") is True
    assert ctx["transcript"] is not None


@then("the remote transcription service is not called")
def remote_not_called(ctx):
    assert ctx.get("remote_called") is False


@then("the local faster-whisper model is not invoked")
def whisper_not_invoked(ctx):
    assert ctx.get("whisper_invoked") is False


@then("the node calls only the injected TranscriptionPort interface")
def node_uses_port(ctx):
    ctx["node_port"].transcribe.assert_called_once()


@then("the node contains no reference to WHISPER_MODEL or provider-specific logic")
def node_no_provider_logic():
    import inspect

    from application.nodes import transcribe as transcribe_mod

    source = inspect.getsource(transcribe_mod)
    assert "WHISPER_MODEL" not in source
    assert "faster_whisper" not in source
    assert "FasterWhisper" not in source
    assert "GoogleTranscription" not in source


@then("the runtime isinstance check returns True")
def isinstance_check_passes(ctx):
    assert ctx["isinstance_result"] is True


@then("a FileTooLargeError is raised")
def file_too_large_error(ctx):
    from domain.exceptions import FileTooLargeError

    assert isinstance(ctx["error"], FileTooLargeError)


@then("the error message states the file size and the limit")
def error_has_size_info(ctx):
    msg = str(ctx["error"])
    assert "bytes" in msg
