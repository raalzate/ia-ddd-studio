"""Pre-populated PromptRegistry singleton with all templates."""

from prompts.registry import PromptRegistry
from prompts.templates.analysis import project_summary_and_critique, refinement, semantic_analysis
from prompts.templates.generation import (
    context_map_specs,
    domain_model_specs,
    gherkin_generation,
)
from prompts.templates.ui import (
    architectural_chat,
    narrative_transform_ui,
    workshop_domain_expert_agent,
    workshop_facilitator_agent,
)

registry = PromptRegistry()

# Application node templates
registry.register(semantic_analysis)
registry.register(refinement)
registry.register(project_summary_and_critique)

# Spec generator UI templates (used by SpecGenerator in specs.py)
registry.register(context_map_specs)
registry.register(domain_model_specs)
registry.register(gherkin_generation)

# UI component templates
registry.register(narrative_transform_ui)
registry.register(architectural_chat)
registry.register(workshop_facilitator_agent)
registry.register(workshop_domain_expert_agent)
