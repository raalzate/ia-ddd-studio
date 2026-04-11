"""Unit tests for src/ui/streamlit_app.py — cached resource builders."""

from unittest.mock import MagicMock, patch


class TestBuildCacheAdapter:
    def test_creates_file_cache(self):
        with patch("infra.adapters.file_cache.FileCacheAdapter") as mock_cls:
            mock_cls.return_value = MagicMock()

            from ui.streamlit_app import _build_cache_adapter

            result = _build_cache_adapter.__wrapped__()
            assert result is not None


class TestGetInferencePort:
    def test_returns_port(self):
        with patch("infra.inference_provider.InferenceProvider.get_inference_port") as mock_get:
            mock_get.return_value = MagicMock()

            from ui.streamlit_app import _get_inference_port

            _get_inference_port.__wrapped__(12345)
            mock_get.assert_called_once()


class TestGetChatAgentPort:
    def test_returns_port(self):
        with patch("infra.inference_provider.InferenceProvider.get_chat_agent_port") as mock_get:
            mock_get.return_value = MagicMock()

            from ui.streamlit_app import _get_chat_agent_port

            _get_chat_agent_port.__wrapped__(12345)
            mock_get.assert_called_once()
