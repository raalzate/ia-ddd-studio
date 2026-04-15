"""Public API for the prompt template module."""

from prompts.catalog import registry
from prompts.errors import (
    DuplicateTemplateError,
    MissingVariableError,
    TemplateNotFoundError,
)
from prompts.registry import PromptRegistry
from prompts.template import PromptTemplate, RenderedPrompt

__all__ = [
    "PromptTemplate",
    "RenderedPrompt",
    "PromptRegistry",
    "MissingVariableError",
    "DuplicateTemplateError",
    "TemplateNotFoundError",
    "registry",
]
