"""PromptTemplate and RenderedPrompt dataclasses.

Uses Python string.Template ($variable syntax) to avoid conflicts with JSON braces
that appear frequently in LLM prompts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from string import Template

from prompts.errors import MissingVariableError

_LANGUAGE_LABELS: dict[str, str] = {
    "es": "Spanish",
    "en": "English",
    "fr": "French",
    "pt": "Portuguese",
    "de": "German",
    "it": "Italian",
}


def _language_constraint(lang_code: str) -> str:
    label = _LANGUAGE_LABELS.get(lang_code.lower(), lang_code)
    return f"LANGUAGE CONSTRAINT: Your entire response MUST be written in {label}. No exceptions."


_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def _extract_variables(text: str | None) -> set[str]:
    """Extract $variable names from template text."""
    if not text:
        return set()
    # Use string.Template's pattern to find all $var and ${var} references
    return {
        m.group("named") or m.group("braced")
        for m in Template.pattern.finditer(text)
        if m.group("named") or m.group("braced")
    }


@dataclass(frozen=True)
class RenderedPrompt:
    """Value object: fully rendered prompt ready for inference."""

    system: str
    user: str | None = None

    def to_string(self, language: str | None = None) -> str:
        """Combine system and user into a single string.

        Appends a language constraint derived from RESPONSE_LANGUAGE env var
        (default: 'es'). Override per-call with the ``language`` argument.

        Returns system + language constraint + user (if present).
        """
        from config.settings import RESPONSE_LANGUAGE

        lang = language if language is not None else RESPONSE_LANGUAGE
        constraint = _language_constraint(lang)
        system_with_lang = f"{self.system}\n\n{constraint}"

        if self.user is not None:
            return f"{system_with_lang}\n\n{self.user}"
        return system_with_lang


@dataclass(frozen=True)
class PromptTemplate:
    """Immutable prompt template with named variables and rendering.

    Uses Python string.Template ($variable syntax) to avoid conflicts
    with JSON braces in prompt text.
    """

    name: str
    description: str
    system: str
    user: str | None = None
    variables: frozenset[str] = field(init=False)

    def __post_init__(self) -> None:
        if not self.name or not _NAME_PATTERN.match(self.name):
            raise ValueError(
                f"Template name '{self.name}' is invalid. "
                "Must match ^[a-z][a-z0-9_]*$ (start with lowercase letter, "
                "use only lowercase letters, digits, and underscores)."
            )
        if not self.system:
            raise ValueError("Template 'system' field must be non-empty.")
        # Auto-extract variables from system + user using object.__setattr__
        # because the dataclass is frozen.
        vars_found = _extract_variables(self.system) | _extract_variables(self.user)
        object.__setattr__(self, "variables", frozenset(vars_found))

    def render(self, **kwargs: str) -> RenderedPrompt:
        """Substitute variables in system and user templates.

        Args:
            **kwargs: Variable name-value pairs.

        Returns:
            RenderedPrompt with fully substituted text.

        Raises:
            MissingVariableError: If any required variable is missing from kwargs.
        """
        missing = self.variables - set(kwargs.keys())
        if missing:
            raise MissingVariableError(self.name, missing)

        rendered_system = Template(self.system).safe_substitute(**kwargs)
        rendered_user = Template(self.user).safe_substitute(**kwargs) if self.user is not None else None

        return RenderedPrompt(system=rendered_system, user=rendered_user)
