"""PromptRegistry: central container for template registration and lookup."""

from __future__ import annotations

from prompts.errors import DuplicateTemplateError, TemplateNotFoundError
from prompts.template import PromptTemplate


class PromptRegistry:
    """Central registry for prompt templates.

    Populated at module import time. Thread-safe for reads after initialization.
    """

    def __init__(self) -> None:
        self._templates: dict[str, PromptTemplate] = {}

    def register(self, template: PromptTemplate) -> None:
        """Register a template by name.

        Raises:
            DuplicateTemplateError: If a template with the same name is already registered.
        """
        if template.name in self._templates:
            raise DuplicateTemplateError(template.name)
        self._templates[template.name] = template

    def get(self, name: str) -> PromptTemplate:
        """Retrieve a template by name.

        Raises:
            TemplateNotFoundError: If no template with this name exists.
        """
        if name not in self._templates:
            raise TemplateNotFoundError(name)
        return self._templates[name]

    def list_all(self) -> list[PromptTemplate]:
        """List all registered templates sorted by name."""
        return sorted(self._templates.values(), key=lambda t: t.name)
