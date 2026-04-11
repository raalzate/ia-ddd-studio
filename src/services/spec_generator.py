import logging

from domain.ports import InferencePort
from models.domain_analysis import DomainAnalysis
from prompts import registry

logger = logging.getLogger(__name__)


class SpecGenerator:
    """
    Generates pure specification artifacts (Gherkin, Domain Models)
    agnostic of the implementation language, following Spec-Driven Development.
    """

    def __init__(self, analysis: DomainAnalysis, inference: InferencePort):
        self.analysis = analysis
        self.inference = inference

    def generate_specs_all(self) -> dict[str, str]:
        return {
            "context_map": self.generate_context_map(),
            "domain_models": self.generate_domain_models(),
        }

    def _invoke_llm(self, system_prompt: str, user_content: str) -> str:
        full_prompt = f"{system_prompt}\n\nCONTENIDO:\n{user_content}"
        return self.inference.invoke_text(full_prompt)

    def generate_context_map(self) -> str:
        data_context = self.analysis.model_dump_json(
            include={"nombre_proyecto", "big_picture", "agregados", "politicas_inter_agregados"}
        )
        rendered = registry.get("context_map_specs").render(data_context=data_context)
        return self._invoke_llm(rendered.system, data_context)

    def generate_domain_models(self) -> str:
        data_context = self.analysis.model_dump_json(
            include={
                "nombre_proyecto",
                "big_picture",
                "agregados",
                "read_models",
                "politicas_inter_agregados",
            }
        )
        rendered = registry.get("domain_model_specs").render(data_context=data_context)
        return self._invoke_llm(rendered.system, data_context)
