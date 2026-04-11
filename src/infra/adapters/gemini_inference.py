"""GeminiInferenceAdapter implementing InferencePort.

Uses ChatGoogleGenerativeAI with with_structured_output.
"""

from __future__ import annotations

import logging
import os
import types
from typing import TypeVar, get_args, get_origin

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import create_model
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from domain.exceptions import ConfigurationError, ServiceUnavailableError

T = TypeVar("T")

logger = logging.getLogger(__name__)


def _is_rate_limit_error(exc: BaseException) -> bool:
    """Return True if the exception is a 429 / RESOURCE_EXHAUSTED error."""
    msg = str(exc).lower()
    return "429" in msg or "resource_exhausted" in msg or "rate limit" in msg


_llm_retry = retry(
    retry=retry_if_exception(_is_rate_limit_error),
    wait=wait_exponential_jitter(initial=10, max=120, jitter=5),
    stop=stop_after_attempt(5),
    before_sleep=lambda rs: logger.warning(
        "Rate limited by Gemini API. Retrying in %.1fs (attempt %d/5)…",
        rs.next_action.sleep,  # type: ignore[union-attr]
        rs.attempt_number,
    ),
    reraise=True,
)


class GeminiInferenceAdapter:
    """InferencePort implementation using Google Gemini."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.1,
    ) -> None:
        self._model_name = model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY", "")
        self._temperature = temperature
        self._llm_instance = None

    @property
    def _llm(self) -> ChatGoogleGenerativeAI:
        """Lazy-loaded LLM instance."""
        if self._llm_instance is None:
            if not self._api_key:
                raise ConfigurationError(
                    "Google API Key is missing. "
                    "Please set GOOGLE_API_KEY environment variable or configure it in the sidebar."
                )
            self._llm_instance = ChatGoogleGenerativeAI(
                model=self._model_name,
                google_api_key=self._api_key,
                temperature=self._temperature,
            )
        return self._llm_instance

    @_llm_retry
    def invoke(self, prompt: str, output_schema: type[T]) -> T:
        """Send prompt and return structured output."""
        try:
            # with_structured_output doesn't support list[X] GenericAlias directly;
            # wrap it in a Pydantic model and unwrap the result.
            if isinstance(output_schema, types.GenericAlias) and get_origin(output_schema) is list:
                item_type = get_args(output_schema)[0]
                wrapper = create_model("_ListWrapper", items=(list[item_type], ...))
                structured_llm = self._llm.with_structured_output(wrapper)
                result = structured_llm.invoke(prompt)
                return result.items  # type: ignore[return-value]
            structured_llm = self._llm.with_structured_output(output_schema)
            return structured_llm.invoke(prompt)
        except Exception as e:
            if "unavailable" in str(e).lower() or "connection" in str(e).lower():
                raise ServiceUnavailableError(str(e)) from e
            raise

    @_llm_retry
    def invoke_text(self, prompt: str) -> str:
        """Send prompt and return raw text response."""
        try:
            response = self._llm.invoke(prompt)
            return response.content
        except Exception as e:
            if "unavailable" in str(e).lower() or "connection" in str(e).lower():
                raise ServiceUnavailableError(str(e)) from e
            raise
