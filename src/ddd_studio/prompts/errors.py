"""Custom exceptions for the prompt template module."""

from __future__ import annotations


class MissingVariableError(ValueError):
    """Raised when render() is called without a required variable."""

    def __init__(self, template_name: str, missing: set[str]) -> None:
        self.template_name = template_name
        self.missing = missing
        missing_str = ", ".join(sorted(missing))
        super().__init__(f"Template '{template_name}' is missing required variables: {missing_str}")


class DuplicateTemplateError(ValueError):
    """Raised when registering a template with an existing name."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Template '{name}' is already registered")


class TemplateNotFoundError(KeyError):
    """Raised when requesting a template that doesn't exist."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Template '{name}' not found in registry")

    def __str__(self) -> str:
        return self.args[0]
