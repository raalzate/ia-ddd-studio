"""Extended tests for input.py — process_input helper."""

from unittest.mock import MagicMock, patch


class _SessionState(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        del self[key]


@patch("ui.components.input.st")
def test_process_input_no_inference(mock_st):
    from ui.components.input import process_input

    mock_st.session_state = _SessionState()
    process_input("text", "hello", "test.txt", None, None)
    mock_st.error.assert_called_once()


@patch("application.pipeline.run_analysis")
@patch("ui.components.input.st")
def test_process_input_text_success(mock_st, mock_run):
    from ui.components.input import process_input

    mock_inference = MagicMock()
    mock_st.session_state = _SessionState(
        {
            "_inference_port": mock_inference,
            "_transcription_port": None,
            "_cache_port": None,
        }
    )

    mock_status = MagicMock()
    mock_status.__enter__ = MagicMock(return_value=mock_status)
    mock_status.__exit__ = MagicMock(return_value=False)
    mock_st.status.return_value = mock_status

    mock_result = MagicMock()
    mock_result.analysis.ddd_specs = None
    mock_result.transcript = "transcribed"
    mock_result.specs = {}
    mock_result.events = []
    mock_result.errors = []
    mock_run.return_value = mock_result

    with patch("ui.components.input._get_draft_service") as mock_draft_svc, patch("ui.utils.storage.save_static_json"):
        mock_draft_svc.return_value.create_draft = MagicMock()

        process_input("text", "some text", "input.txt", None, None)

    mock_run.assert_called_once()
    assert "analysis_result" in mock_st.session_state


@patch("application.pipeline.run_analysis")
@patch("ui.components.input.st")
def test_process_input_audio_success(mock_st, mock_run):
    from ui.components.input import process_input

    mock_inference = MagicMock()
    mock_st.session_state = _SessionState(
        {
            "_inference_port": mock_inference,
            "_transcription_port": MagicMock(),
            "_cache_port": MagicMock(),
        }
    )

    mock_status = MagicMock()
    mock_status.__enter__ = MagicMock(return_value=mock_status)
    mock_status.__exit__ = MagicMock(return_value=False)
    mock_st.status.return_value = mock_status

    mock_audio = MagicMock()
    mock_audio.getvalue.return_value = b"audio_data"

    mock_result = MagicMock()
    mock_result.analysis.ddd_specs = {"context_map": "diagram"}
    mock_result.transcript = "transcribed"
    mock_result.specs = {"context_map": "diagram"}
    mock_result.events = []
    mock_result.errors = []
    mock_run.return_value = mock_result

    with patch("ui.components.input._get_draft_service") as mock_draft_svc, patch("ui.utils.storage.save_static_json"):
        mock_draft_svc.return_value.create_draft = MagicMock()

        process_input("audio", mock_audio, "recording.wav", None, "context text")

    mock_run.assert_called_once()
    req = mock_run.call_args[1]["request"]
    assert req.audio_bytes == b"audio_data"


@patch("application.pipeline.run_analysis")
@patch("ui.components.input.st")
def test_process_input_handles_error(mock_st, mock_run):
    from ui.components.input import process_input

    mock_st.session_state = _SessionState(
        {
            "_inference_port": MagicMock(),
            "_transcription_port": None,
            "_cache_port": None,
        }
    )

    mock_status = MagicMock()
    mock_status.__enter__ = MagicMock(return_value=mock_status)
    mock_status.__exit__ = MagicMock(return_value=False)
    mock_st.status.return_value = mock_status

    mock_run.side_effect = RuntimeError("Pipeline failed")

    process_input("text", "some text", "input.txt", None, None)

    mock_st.error.assert_called()


@patch("application.pipeline.run_analysis")
@patch("ui.components.input.st")
def test_process_input_with_context_pdf(mock_st, mock_run):
    from ui.components.input import process_input

    mock_st.session_state = _SessionState(
        {
            "_inference_port": MagicMock(),
            "_transcription_port": None,
            "_cache_port": None,
        }
    )

    mock_status = MagicMock()
    mock_status.__enter__ = MagicMock(return_value=mock_status)
    mock_status.__exit__ = MagicMock(return_value=False)
    mock_st.status.return_value = mock_status

    mock_result = MagicMock()
    mock_result.analysis.ddd_specs = None
    mock_result.transcript = "text"
    mock_result.specs = {}
    mock_result.events = []
    mock_result.errors = []
    mock_run.return_value = mock_result

    mock_pdf = MagicMock()
    mock_pdf.name = "doc.pdf"

    with (
        patch("ui.components.input._pdf_to_markdown", return_value="# PDF Content"),
        patch("ui.components.input._get_draft_service") as mock_draft_svc,
        patch("ui.utils.storage.save_static_json"),
    ):
        mock_draft_svc.return_value.create_draft = MagicMock()

        process_input("text", "text", "input.txt", mock_pdf, "manual context")

    # Context should include both PDF and manual text
    req = mock_run.call_args[1]["request"]
    assert "PDF Content" in req.context
    assert "manual context" in req.context


@patch("application.pipeline.run_analysis")
@patch("ui.components.input.st")
def test_process_input_with_errors_shows_warnings(mock_st, mock_run):
    from ui.components.input import process_input

    mock_st.session_state = _SessionState(
        {
            "_inference_port": MagicMock(),
            "_transcription_port": None,
            "_cache_port": None,
        }
    )

    mock_status = MagicMock()
    mock_status.__enter__ = MagicMock(return_value=mock_status)
    mock_status.__exit__ = MagicMock(return_value=False)
    mock_st.status.return_value = mock_status

    mock_error = MagicMock()
    mock_error.node_name = "test_node"
    mock_error.message = "warning msg"

    mock_result = MagicMock()
    mock_result.analysis.ddd_specs = None
    mock_result.transcript = "text"
    mock_result.specs = {}
    mock_result.events = []
    mock_result.errors = [mock_error]
    mock_run.return_value = mock_result

    with patch("ui.components.input._get_draft_service") as mock_draft_svc, patch("ui.utils.storage.save_static_json"):
        mock_draft_svc.return_value.create_draft = MagicMock()

        process_input("text", "text", "input.txt", None, None)

    mock_st.warning.assert_called()
