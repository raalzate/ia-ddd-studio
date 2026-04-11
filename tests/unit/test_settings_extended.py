"""Extended unit tests for src/config/settings.py — load_api_key and TokenUsageCallback."""

from unittest.mock import MagicMock

import pytest


class TestLoadApiKey:
    def test_returns_when_env_vars_set(self, monkeypatch):
        from config import settings

        monkeypatch.setattr(settings, "GOOGLE_API_KEY", "test-key")
        monkeypatch.setattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
        settings.load_api_key()  # Should not raise

    def test_raises_when_no_env_and_no_persisted(self, monkeypatch):
        from config import settings

        monkeypatch.setattr(settings, "GOOGLE_API_KEY", None)
        monkeypatch.setattr(settings, "GEMINI_MODEL", None)

        # Mock the import inside load_api_key
        import types

        mock_storage = types.ModuleType("ui.utils.storage")
        mock_storage.load_llm_config = lambda: None
        monkeypatch.setitem(__import__("sys").modules, "ui.utils.storage", mock_storage)

        with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
            settings.load_api_key()

    def test_returns_when_env_key_set_but_model_default(self, monkeypatch):
        from config import settings

        monkeypatch.setattr(settings, "GOOGLE_API_KEY", "test-key")
        monkeypatch.setattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
        settings.load_api_key()  # Should not raise


class TestTokenUsageCallback:
    def test_initial_state(self):
        from config.settings import TokenUsageCallback

        cb = TokenUsageCallback()
        assert cb.input_tokens == 0
        assert cb.output_tokens == 0
        assert cb.cost_msg == ""

    def test_on_llm_end_with_token_usage(self):
        from config.settings import TokenUsageCallback

        cb = TokenUsageCallback()
        mock_response = MagicMock()
        mock_response.llm_output = {
            "token_usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            }
        }
        cb.on_llm_end(mock_response)
        assert cb.input_tokens == 100
        assert cb.output_tokens == 50
        assert "100" in cb.cost_msg
        assert "50" in cb.cost_msg
        assert "$" in cb.cost_msg

    def test_on_llm_end_with_google_style_keys(self):
        from config.settings import TokenUsageCallback

        cb = TokenUsageCallback()
        mock_response = MagicMock()
        mock_response.llm_output = {
            "token_usage": {
                "prompt_token_count": 200,
                "candidates_token_count": 100,
            }
        }
        cb.on_llm_end(mock_response)
        assert cb.input_tokens == 200
        assert cb.output_tokens == 100

    def test_on_llm_end_with_empty_usage(self):
        from config.settings import TokenUsageCallback

        cb = TokenUsageCallback()
        mock_response = MagicMock()
        mock_response.llm_output = {"token_usage": {}}
        cb.on_llm_end(mock_response)
        assert cb.input_tokens == 0
        assert cb.output_tokens == 0
        assert "Total: $0.000000" in cb.cost_msg

    def test_cost_calculation(self):
        from config.settings import PRICE_PER_1K_INPUT_TOKENS, PRICE_PER_1K_OUTPUT_TOKENS, TokenUsageCallback

        cb = TokenUsageCallback()
        mock_response = MagicMock()
        mock_response.llm_output = {"token_usage": {"input_tokens": 1000, "output_tokens": 1000}}
        cb.on_llm_end(mock_response)

        expected_input_cost = PRICE_PER_1K_INPUT_TOKENS
        expected_output_cost = PRICE_PER_1K_OUTPUT_TOKENS
        expected_total = expected_input_cost + expected_output_cost
        assert f"${expected_total:.6f}" in cb.cost_msg
