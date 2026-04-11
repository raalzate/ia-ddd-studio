"""Validation test for settings: no local model path fields.

[TS-006]
"""

import ast
import pathlib

import pytest

pytestmark = pytest.mark.offline


class TestSettingsNoLocalModelPaths:
    """[TS-006] src/config/settings.py must contain no local model path fields."""

    def test_settings_has_no_local_model_references(self):
        """Local model constants must not point to real paths or models."""
        settings_path = pathlib.Path("src/config/settings.py")
        assert settings_path.exists(), "src/config/settings.py must exist"

        source = settings_path.read_text()

        # These patterns must never appear (active local model usage)
        forbidden_patterns = [
            "faster_whisper",
            "llama_cpp",
            "gguf",
            ".bin",
        ]
        for pattern in forbidden_patterns:
            assert pattern.lower() not in source.lower(), (
                f"src/config/settings.py references local model pattern '{pattern}'"
            )

        # Legacy aliases must exist but be set to None (backward compat only)
        # Note: WHISPER_MODEL is excluded — feature 006 re-enables it via os.getenv()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in (
                        "LOCAL_MODEL_PATH",
                        "LLM_MODEL_PATH",
                    ):
                        assert isinstance(node.value, ast.Constant) and node.value.value is None, (
                            f"{target.id} must be set to None (legacy alias only)"
                        )

    def test_settings_has_google_api_key(self):
        settings_path = pathlib.Path("src/config/settings.py")
        source = settings_path.read_text()
        assert "GOOGLE_API_KEY" in source, "src/config/settings.py must reference GOOGLE_API_KEY"

    def test_settings_has_gemini_model(self):
        settings_path = pathlib.Path("src/config/settings.py")
        source = settings_path.read_text()
        assert "GEMINI_MODEL" in source or "gemini" in source.lower(), (
            "src/config/settings.py must reference Gemini model"
        )
