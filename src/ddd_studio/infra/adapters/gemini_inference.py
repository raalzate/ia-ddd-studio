## GeminiInferenceAdapter con Retraso de Seguridad

"""GeminiInferenceAdapter implementing InferencePort.

Uses ChatGoogleGenerativeAI with with_structured_output.
"""

from __future__ import annotations

import logging
import os
import time
import types
from typing import TypeVar, get_args, get_origin

from domain.exceptions import ConfigurationError, ServiceUnavailableError
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import create_model
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

T = TypeVar("T")

logger = logging.getLogger(__name__)


def _is_rate_limit_error(exc: BaseException) -> bool:
    """Return True for transient Gemini errors worth retrying."""
    msg = str(exc).lower()
    return (
        "429" in msg
        or "resource_exhausted" in msg
        or "rate limit" in msg
        or "503" in msg
        or "unavailable" in msg
        or "high_demand" in msg
    )


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

    _GREEDY_TEMPERATURE = 0.0
    _GREEDY_TOP_K = 1
    _GREEDY_TOP_P = 1.0

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self._model_name = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY", "")
        self._llm_instance = None

    @property
    def _llm(self) -> ChatGoogleGenerativeAI:
        """Lazy-loaded LLM instance with hardcoded greedy decoding."""
        if self._llm_instance is None:
            if not self._api_key:
                raise ConfigurationError("Google API Key is missing. Please set GOOGLE_API_KEY environment variable.")
            self._llm_instance = ChatGoogleGenerativeAI(
                model=self._model_name,
                google_api_key=self._api_key,
                temperature=self._GREEDY_TEMPERATURE,
                top_k=self._GREEDY_TOP_K,
                top_p=self._GREEDY_TOP_P,
            )
        return self._llm_instance

    @_llm_retry
    def invoke(self, prompt: str, output_schema: type[T]) -> T:
        """Send prompt and return structured output."""
        # Sleep de 5 segundos para evitar saturar la API en llamadas paralelas
        time.sleep(5)

        start_time = time.time()
        schema_name = getattr(output_schema, "__name__", str(output_schema))

        try:
            if isinstance(output_schema, types.GenericAlias) and get_origin(output_schema) is list:
                item_type = get_args(output_schema)[0]
                wrapper = create_model("_ListWrapper", items=(list[item_type], ...))
                structured_llm = self._llm.with_structured_output(wrapper)
                result = structured_llm.invoke(prompt)

                duration = time.time() - start_time
                print(f"      [LLM] Extracción finalizada ({schema_name}) en {duration:.1f}s")
                return result.items  # type: ignore[return-value]

            structured_llm = self._llm.with_structured_output(output_schema)
            result = structured_llm.invoke(prompt)

            duration = time.time() - start_time
            print(f"      [LLM] Extracción finalizada ({schema_name}) en {duration:.1f}s")
            return result

        except Exception as e:
            if "unavailable" in str(e).lower() or "connection" in str(e).lower():
                raise ServiceUnavailableError(str(e)) from e
            raise

    @_llm_retry
    def invoke_text(self, prompt: str) -> str:
        """Send prompt and return raw text response."""
        # Sleep de 1 segundos para evitar saturar la API en llamadas paralelas
        time.sleep(1)

        start_time = time.time()
        try:
            response = self._llm.invoke(prompt)
            duration = time.time() - start_time
            print(f"      [LLM] Inferencia de texto finalizada en {duration:.1f}s")
            return str(response.content)
        except Exception as e:
            if "unavailable" in str(e).lower() or "connection" in str(e).lower():
                raise ServiceUnavailableError(str(e)) from e
            raise
