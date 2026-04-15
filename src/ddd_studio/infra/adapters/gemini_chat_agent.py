"""GeminiChatAgentAdapter implementing ChatAgentPort.

Uses ChatGoogleGenerativeAI.bind_tools with a manual ReAct loop.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from domain.models.tool_schemas import AgentResponse, ToolExecution
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from services.model_accessor import ModelAccessor
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

MAX_ITERATIONS = 5

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


class GeminiChatAgentAdapter:
    """ChatAgentPort implementation using Gemini with tool calling."""

    # Chat agent stays greedy too — tool-calling benefits from deterministic
    # routing. Any "creativity" should live in the prompt, not in sampling.
    _GREEDY_TEMPERATURE = 0.0
    _GREEDY_TOP_K = 1
    _GREEDY_TOP_P = 1.0

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self._model_name = model
        self._api_key = api_key
        self._llm_instance = None

    @property
    def _llm(self) -> Any:
        """Lazy-loaded LLM instance with hardcoded greedy decoding."""
        if self._llm_instance is None:
            from domain.exceptions import ConfigurationError
            from langchain_google_genai import ChatGoogleGenerativeAI

            if not self._api_key:
                raise ConfigurationError(
                    "Google API Key is missing. Please configure it in the sidebar to use the Chat Agent."
                )
            self._llm_instance = ChatGoogleGenerativeAI(
                model=self._model_name,
                google_api_key=self._api_key,
                temperature=self._GREEDY_TEMPERATURE,
                top_k=self._GREEDY_TOP_K,
                top_p=self._GREEDY_TOP_P,
            )
        return self._llm_instance

    @staticmethod
    @_llm_retry
    def _invoke_with_retry(llm: Any, messages: list) -> Any:
        """Invoke the LLM with retry on rate-limit errors."""
        return llm.invoke(messages)

    def run(
        self,
        user_message: str,
        history: list[dict[str, str]],
        system_prompt: str,
        model_accessor: ModelAccessor,
    ) -> AgentResponse:
        """Execute one agent turn with ReAct loop."""
        from services.agent_tools import create_tools

        tools = create_tools(model_accessor)
        tool_map = {t.name: t for t in tools}

        llm_with_tools = self._llm.bind_tools(tools)

        messages: list = [SystemMessage(content=system_prompt)]
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=user_message))

        tool_executions: list[ToolExecution] = []
        iterations = 0

        while iterations < MAX_ITERATIONS:
            response = self._invoke_with_retry(llm_with_tools, messages)
            messages.append(response)

            if not response.tool_calls:
                break

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call.get("id", f"call_{iterations}")

                tool_fn = tool_map.get(tool_name)
                if tool_fn:
                    try:
                        result_str = tool_fn.invoke(tool_args)
                        success = True
                        try:
                            parsed = json.loads(result_str)
                            success = parsed.get("success", True)
                        except (json.JSONDecodeError, AttributeError):
                            pass
                    except Exception as e:
                        result_str = json.dumps(
                            {
                                "success": False,
                                "message": str(e),
                                "affected_elements": [],
                            }
                        )
                        success = False
                else:
                    result_str = json.dumps(
                        {
                            "success": False,
                            "message": f"Unknown tool: {tool_name}",
                            "affected_elements": [],
                        }
                    )
                    success = False

                messages.append(ToolMessage(content=result_str, tool_call_id=tool_id))
                tool_executions.append(
                    ToolExecution(
                        tool_name=tool_name,
                        arguments=tool_args,
                        result=result_str,
                        success=success,
                    )
                )

            iterations += 1

        final_content = response.content if response.content else ""

        if iterations >= MAX_ITERATIONS and response.tool_calls:
            final_content = "I reached the maximum number of tool calls. Here's what I found so far."

        # When the LLM returns empty content after successful tool calls,
        # synthesize a human-readable summary so the chat bubble isn't blank.
        if not final_content.strip() and tool_executions:
            summary_parts = []
            for te in tool_executions:
                try:
                    parsed = json.loads(te.result)
                    msg = parsed.get("message", "")
                    icon = "✅" if te.success else "❌"
                    summary_parts.append(f"{icon} **{te.tool_name}**: {msg}")
                except (json.JSONDecodeError, AttributeError):
                    summary_parts.append(f"🔧 **{te.tool_name}**: ejecutado")
            final_content = "### Operaciones realizadas\n\n" + "\n".join(summary_parts)

        return AgentResponse(
            content=final_content,
            tool_executions=tool_executions,
        )
