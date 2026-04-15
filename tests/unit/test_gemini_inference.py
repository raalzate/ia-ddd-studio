"""Unit tests for GeminiInferenceAdapter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from domain.exceptions import ServiceUnavailableError
from infra.adapters.gemini_inference import GeminiInferenceAdapter
from pydantic import BaseModel


class MockModel(BaseModel):
    name: str
    count: int


@patch("infra.adapters.gemini_inference.ChatGoogleGenerativeAI")
def test_gemini_invoke_structured(mock_chat):
    """Verify GeminiInferenceAdapter calls with_structured_output correctly."""
    adapter = GeminiInferenceAdapter(api_key="fake")

    mock_llm_instance = mock_chat.return_value
    mock_structured = MagicMock()
    mock_llm_instance.with_structured_output.return_value = mock_structured

    expected_result = MockModel(name="test", count=5)
    mock_structured.invoke.return_value = expected_result

    result = adapter.invoke("prompt", MockModel)

    assert result == expected_result
    mock_llm_instance.with_structured_output.assert_called_once_with(MockModel)
    mock_structured.invoke.assert_called_once_with("prompt")


@patch("infra.adapters.gemini_inference.ChatGoogleGenerativeAI")
def test_gemini_invoke_list_structured(mock_chat):
    """Verify GeminiInferenceAdapter handles list[T] by wrapping it."""
    adapter = GeminiInferenceAdapter(api_key="fake")

    mock_llm_instance = mock_chat.return_value
    mock_structured = MagicMock()
    mock_llm_instance.with_structured_output.return_value = mock_structured

    # The adapter wraps list[MockModel] in a _ListWrapper model
    mock_response = MagicMock()
    mock_response.items = [MockModel(name="a", count=1)]
    mock_structured.invoke.return_value = mock_response

    result = adapter.invoke("prompt", list[MockModel])

    assert len(result) == 1
    assert result[0].name == "a"
    # Check that it was wrapped (the argument to with_structured_output should be a Pydantic model)
    wrapper_model = mock_llm_instance.with_structured_output.call_args[0][0]
    assert wrapper_model.__name__ == "_ListWrapper"


@patch("infra.adapters.gemini_inference.ChatGoogleGenerativeAI")
def test_gemini_invoke_text(mock_chat):
    """Verify GeminiInferenceAdapter.invoke_text returns raw content."""
    adapter = GeminiInferenceAdapter(api_key="fake")

    mock_llm_instance = mock_chat.return_value
    mock_response = MagicMock()
    mock_response.content = "raw response"
    mock_llm_instance.invoke.return_value = mock_response

    result = adapter.invoke_text("prompt")

    assert result == "raw response"
    mock_llm_instance.invoke.assert_called_once_with("prompt")


@patch("infra.adapters.gemini_inference.ChatGoogleGenerativeAI")
def test_gemini_service_unavailable(mock_chat):
    """Verify conversion of network errors to ServiceUnavailableError."""
    adapter = GeminiInferenceAdapter(api_key="fake")
    mock_llm_instance = mock_chat.return_value
    mock_llm_instance.invoke.side_effect = Exception("Connection unavailable")

    with pytest.raises(ServiceUnavailableError):
        adapter.invoke_text("prompt")
