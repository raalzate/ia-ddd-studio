"""Extended tests for chat.py — _trigger_summary_and_critique and render_chat_tab."""

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


class TestTriggerSummaryAndCritique:
    @patch("ui.components.chat.st")
    def test_returns_early_when_no_inference(self, mock_st):
        from ui.components.chat import _trigger_summary_and_critique

        mock_st.session_state = _SessionState()
        _trigger_summary_and_critique(MagicMock())

    @patch("ui.components.chat.registry")
    @patch("ui.components.chat.st")
    def test_generates_summary(self, mock_st, mock_registry):
        from ui.components.chat import _trigger_summary_and_critique

        mock_inference = MagicMock()
        mock_inference.invoke_text.return_value = "Summary text"
        mock_st.session_state = _SessionState({"_inference_port": mock_inference, "chat_messages": []})
        mock_st.spinner.return_value.__enter__ = MagicMock()
        mock_st.spinner.return_value.__exit__ = MagicMock()

        mock_template = MagicMock()
        mock_template.render.return_value.to_string.return_value = "system prompt"
        mock_registry.get.return_value = mock_template

        analysis = MagicMock()
        analysis.model_dump_json.return_value = "{}"

        _trigger_summary_and_critique(analysis)

        assert len(mock_st.session_state["chat_messages"]) == 1
        assert mock_st.session_state["chat_messages"][0]["is_summary"] is True

    @patch("ui.components.chat.registry")
    @patch("ui.components.chat.st")
    def test_skips_if_already_generated(self, mock_st, mock_registry):
        from ui.components.chat import _trigger_summary_and_critique

        mock_st.session_state = _SessionState(
            {
                "_inference_port": MagicMock(),
                "chat_messages": [{"role": "assistant", "content": "prev", "is_summary": True}],
            }
        )

        _trigger_summary_and_critique(MagicMock())
        assert len(mock_st.session_state["chat_messages"]) == 1

    @patch("ui.components.chat.registry")
    @patch("ui.components.chat.st")
    def test_handles_inference_error(self, mock_st, mock_registry):
        from ui.components.chat import _trigger_summary_and_critique

        mock_inference = MagicMock()
        mock_inference.invoke_text.side_effect = RuntimeError("API error")
        mock_st.session_state = _SessionState({"_inference_port": mock_inference, "chat_messages": []})
        mock_st.spinner.return_value.__enter__ = MagicMock()
        mock_st.spinner.return_value.__exit__ = MagicMock()

        mock_template = MagicMock()
        mock_template.render.return_value.to_string.return_value = "prompt"
        mock_registry.get.return_value = mock_template

        analysis = MagicMock()
        analysis.model_dump_json.return_value = "{}"

        _trigger_summary_and_critique(analysis)

        assert len(mock_st.session_state["chat_messages"]) == 1
        assert "No se pudo generar" in mock_st.session_state["chat_messages"][0]["content"]


class TestRenderChatTab:
    @patch("ui.components.chat.st")
    def test_warns_when_no_engine(self, mock_st):
        from ui.components.chat import render_chat_tab

        mock_st.session_state = _SessionState()
        render_chat_tab(MagicMock())
        mock_st.warning.assert_called_once()
