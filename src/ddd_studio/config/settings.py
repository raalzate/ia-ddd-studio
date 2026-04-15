import os
from typing import Any

from dotenv import load_dotenv
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

# Load environment variables
load_dotenv()

# Configuration constants — remote-only, no local model paths
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("LLM_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
TRANSCRIPTION_MAX_BYTES = int(os.getenv("TRANSCRIPTION_MAX_BYTES", str(10 * 1024 * 1024)))

# Legacy aliases for backward compatibility with existing UI/services code
LLM_MODEL = GEMINI_MODEL
LLM_API_KEY = GOOGLE_API_KEY
LOCAL_MODEL_PATH = None  # Removed — remote-only inference
LLM_MODEL_PATH = None  # Removed — remote-only inference
WHISPER_MODEL = os.getenv("WHISPER_MODEL") or None

RESPONSE_LANGUAGE = os.getenv("RESPONSE_LANGUAGE", "es")

PRICE_PER_1K_INPUT_TOKENS = 0.0035  # $3.50 / 1M tokens
PRICE_PER_1K_OUTPUT_TOKENS = 0.0105  # $10.50 / 1M tokens


def load_api_key():
    """Validate that API key and model are available (env or persisted config)."""
    if GOOGLE_API_KEY and GEMINI_MODEL:
        return
    # Fallback: check for a persisted config saved by the UI
    try:
        from ui.utils.storage import load_llm_config

        saved = load_llm_config()
        if saved and saved.get("api_key") and saved.get("model_name"):
            return
    except Exception:
        pass
    raise ValueError("GOOGLE_API_KEY or GEMINI_MODEL not set in env")


class TokenUsageCallback(BaseCallbackHandler):
    """Callback to capture input and output token usage."""

    def __init__(self):
        super().__init__()
        self.input_tokens = 0
        self.output_tokens = 0
        self.cost_msg = ""

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Called when the LLM finishes execution."""
        usage = response.llm_output.get("token_usage", {})

        if usage:
            self.input_tokens = usage.get("input_tokens", 0)
            self.output_tokens = usage.get("output_tokens", 0)

            if self.input_tokens == 0:
                self.input_tokens = usage.get("prompt_token_count", 0)
            if self.output_tokens == 0:
                self.output_tokens = usage.get("candidates_token_count", 0)

        input_cost = (self.input_tokens / 1000) * PRICE_PER_1K_INPUT_TOKENS
        output_cost = (self.output_tokens / 1000) * PRICE_PER_1K_OUTPUT_TOKENS
        total_cost = input_cost + output_cost

        self.cost_msg = (
            f"Input: {self.input_tokens} tk (${input_cost:.6f}) | "
            f"Output: {self.output_tokens} tk (${output_cost:.6f}) | "
            f"Total: ${total_cost:.6f} (Model: {GEMINI_MODEL})"
        )
