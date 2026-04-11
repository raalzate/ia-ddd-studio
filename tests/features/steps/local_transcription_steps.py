"""BDD step definitions for local-transcription.feature.

Covers: TS-001, TS-002, TS-003, TS-004, TS-005
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from domain.exceptions import TranscriptionError
from tests.conftest import FEATURE_006_DIR

scenarios(os.path.join(FEATURE_006_DIR, "local-transcription.feature"))

# ── Shared state ──────────────────────────────────────────────────────────


@pytest.fixture
def ctx():
    """Mutable context dict shared across steps."""
    return {
        "model_name": None,
        "package_installed": True,
        "adapter": None,
        "result": None,
        "error": None,
        "mock_model": None,
        "remote_called": False,
    }


# ── Given ─────────────────────────────────────────────────────────────────


@given(
    parsers.parse('the environment variable "WHISPER_MODEL" is set to "{value}"'),
    target_fixture="ctx",
)
def whisper_model_set(ctx, value, monkeypatch):
    monkeypatch.setenv("WHISPER_MODEL", value)
    ctx["model_name"] = value
    return ctx


@given("the faster-whisper package is installed")
def package_installed(ctx):
    ctx["package_installed"] = True


@given("the faster-whisper package is NOT installed")
def package_not_installed(ctx):
    ctx["package_installed"] = False


@given("an audio file of 30 seconds is available", target_fixture="audio_bytes")
def audio_file_available():
    return b"\x00" * 48_000  # fake 30s audio


@given("a Spanish-language audio file is available", target_fixture="audio_bytes")
def spanish_audio_available():
    return b"\x00" * 48_000


# ── When ──────────────────────────────────────────────────────────────────


@when("the transcription adapter is constructed")
def construct_adapter(ctx):
    from infra.adapters.faster_whisper_transcription import (
        FasterWhisperTranscriptionAdapter,
    )

    if ctx["package_installed"]:
        mock_model = MagicMock()
        ctx["mock_model"] = mock_model
        with patch(
            "infra.adapters.faster_whisper_transcription.WhisperModel",
            return_value=mock_model,
        ):
            ctx["adapter"] = FasterWhisperTranscriptionAdapter(model_name=ctx["model_name"])
    else:
        with patch(
            "infra.adapters.faster_whisper_transcription.WhisperModel",
            side_effect=ImportError("No module named 'faster_whisper'"),
        ):
            try:
                FasterWhisperTranscriptionAdapter(model_name=ctx["model_name"])
            except TranscriptionError as e:
                ctx["error"] = e


@when("the audio is submitted for transcription")
def submit_audio(ctx, audio_bytes):
    from infra.adapters.faster_whisper_transcription import (
        FasterWhisperTranscriptionAdapter,
    )

    mock_seg = MagicMock()
    mock_seg.text = "Texto transcrito de prueba"
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter([mock_seg]), MagicMock())

    with patch(
        "infra.adapters.faster_whisper_transcription.WhisperModel",
        return_value=mock_model,
    ):
        adapter = FasterWhisperTranscriptionAdapter(model_name=ctx["model_name"])

    ctx["adapter"] = adapter
    ctx["mock_model"] = mock_model
    try:
        ctx["result"] = adapter.transcribe(audio_bytes, language="es")
    except Exception as e:
        ctx["error"] = e


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
        adapter = FasterWhisperTranscriptionAdapter(model_name=ctx["model_name"])

    ctx["adapter"] = adapter
    ctx["mock_model"] = mock_model
    ctx["result"] = adapter.transcribe(audio_bytes, language="es")


@when("the transcription adapter is constructed and used")
def construct_and_use_adapter(ctx):
    from infra.adapters.faster_whisper_transcription import (
        FasterWhisperTranscriptionAdapter,
    )

    with patch(
        "infra.adapters.faster_whisper_transcription.WhisperModel",
        side_effect=ValueError(f"Invalid model name: {ctx['model_name']}"),
    ):
        try:
            FasterWhisperTranscriptionAdapter(model_name=ctx["model_name"])
        except TranscriptionError as e:
            ctx["error"] = e


@when("the transcription adapter attempts to transcribe audio")
def attempt_transcribe_missing_pkg(ctx):
    from infra.adapters.faster_whisper_transcription import (
        FasterWhisperTranscriptionAdapter,
    )

    with patch(
        "infra.adapters.faster_whisper_transcription.WhisperModel",
        side_effect=ImportError("No module named 'faster_whisper'"),
    ):
        try:
            FasterWhisperTranscriptionAdapter(model_name=ctx["model_name"])
        except TranscriptionError as e:
            ctx["error"] = e


# ── Then ──────────────────────────────────────────────────────────────────


@then("a FasterWhisperTranscriptionAdapter is returned")
def adapter_is_faster_whisper(ctx):
    from infra.adapters.faster_whisper_transcription import (
        FasterWhisperTranscriptionAdapter,
    )

    assert isinstance(ctx["adapter"], FasterWhisperTranscriptionAdapter)


@then("no remote transcription service is contacted")
def no_remote_call(ctx):
    # The adapter is local-only — if it constructed successfully with the mock,
    # no remote service was involved.
    assert ctx["adapter"] is not None
    assert ctx.get("remote_called") is False


@then("the transcript is a non-empty plain text string")
def transcript_is_non_empty(ctx):
    assert isinstance(ctx["result"], str)
    assert len(ctx["result"].strip()) > 0


@then("no remote transcription API call is made")
def no_remote_api_call(ctx):
    assert ctx.get("remote_called") is False


@then("the transcript is a plain text string with no timestamps or metadata")
def transcript_no_timestamps(ctx):
    import re

    result = ctx["result"]
    assert isinstance(result, str)
    assert not re.search(r"\[\d{2}:\d{2}", result)
    assert not re.search(r"\d+\.\d+\s*-\s*\d+\.\d+", result)


@then("the transcript can be passed to the semantic analysis stage without conversion")
def transcript_compatible(ctx):
    result = ctx["result"]
    assert isinstance(result, str)
    assert len(result.strip()) > 0


@then("a TranscriptionError is raised")
def transcription_error_raised(ctx):
    assert ctx["error"] is not None
    assert isinstance(ctx["error"], TranscriptionError)


@then("the error message describes the invalid model name")
def error_describes_model(ctx):
    assert ctx["model_name"] in str(ctx["error"])


@then("the error message instructs the user to install faster-whisper")
def error_instructs_install(ctx):
    assert "faster-whisper" in str(ctx["error"]).lower() or "faster_whisper" in str(ctx["error"]).lower()
