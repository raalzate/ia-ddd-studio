"""Extended tests for sidebar.py — render functions."""

from unittest.mock import MagicMock, patch


class _SessionState(dict):
    """Dict subclass that supports attribute-style access like Streamlit session_state."""

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            raise AttributeError(key)


@patch("ui.components.sidebar.st")
def test_render_history_no_drafts(mock_st):
    from ui.components.sidebar import _render_history_section

    mock_st.session_state = _SessionState()

    mock_draft_service = MagicMock()
    mock_draft_service.list_drafts.return_value = []

    with patch("ui.components.sidebar._get_draft_service", return_value=mock_draft_service):
        mock_st.expander.return_value.__enter__ = MagicMock()
        mock_st.expander.return_value.__exit__ = MagicMock()

        _render_history_section()

        mock_st.info.assert_called_once()


@patch("ui.components.sidebar.DomainAnalysis")
@patch("ui.components.sidebar.st")
def test_load_draft_into_session_success(mock_st, mock_da):
    from ui.components.sidebar import _load_draft_into_session

    mock_service = MagicMock()
    mock_draft = MagicMock()
    mock_draft.snapshot = {"nombre_proyecto": "Test"}
    mock_service.get_draft.return_value = mock_draft

    mock_analysis = MagicMock()
    mock_da.model_validate.return_value = mock_analysis

    mock_st.session_state = _SessionState()

    _load_draft_into_session(mock_service, "draft-123", "gen-456")

    assert "analysis_result" in mock_st.session_state
    mock_st.rerun.assert_called_once()


@patch("ui.components.sidebar.st")
def test_load_draft_into_session_not_found(mock_st):
    from ui.components.sidebar import _load_draft_into_session

    mock_service = MagicMock()
    mock_service.get_draft.return_value = None

    mock_st.session_state = _SessionState()

    _load_draft_into_session(mock_service, "bad-id", "gen-456")

    mock_st.error.assert_called_once()


@patch("ui.components.sidebar.InferenceProvider")
@patch("ui.components.sidebar.st")
def test_render_ai_config(mock_st, mock_provider):
    from ui.components.sidebar import _render_ai_config

    mock_provider.get_config.return_value = {
        "model_name": "gemini-2.5-flash",
        "api_key": "test-key",
    }

    mock_st.expander.return_value.__enter__ = MagicMock()
    mock_st.expander.return_value.__exit__ = MagicMock()
    mock_st.text_input.return_value = "gemini-2.5-flash"
    mock_st.button.return_value = False

    _render_ai_config()

    mock_st.expander.assert_called_once()
