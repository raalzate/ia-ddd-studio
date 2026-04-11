"""NLP Extractor Service — Deterministic entity extraction using spaCy.

Provides a deterministic pre-processing layer that extracts actors,
aggregates, and potential commands/events from raw transcripts to ground
the Event Storming generation on actual linguistic boundaries.

Extraction strategy (aligned with DomainAnalysis taxonomy):
- **Actors**: nominal subjects (nsubj) → map to ElementType "Actor"
- **Domain terms**: clean nouns + compound noun chunks → candidates for
  "Agregado", "Entidad Raíz", or Value Objects
- **Potential commands**: verb + direct-object pairs → ElementType "Comando"
- **Action verbs**: non-generic verbs → seeds for "Evento" (past-participle)
- **Entities**: spaCy NER (ORG/PER) → candidates for "Sistema Externo"
"""

from __future__ import annotations

import functools
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Ruido común en narrativas técnicas/negocio en español.
# Filtramos estos para evitar que el LLM cree Agregados como "Sistema"
# o Comandos como "Hacer dato".
GENERIC_NOUNS = {
    "sistema", "aplicación", "vez", "manera", "forma", "información",
    "dato", "proceso", "parte", "paso", "cosa", "tipo", "caso", "tema",
    "momento", "nivel", "uso", "área",
}
GENERIC_VERBS = {
    "ser", "estar", "haber", "tener", "hacer", "poder", "deber",
    "querer", "ir", "dar", "decir", "parecer", "ver", "saber",
    "llegar", "pasar", "quedar", "poner", "seguir", "encontrar",
}

_MIN_LEMMA_LEN = 3

# ---------------------------------------------------------------------------
# Lazy spaCy model loading (cached across calls)
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=1)
def _load_spacy_model(model_name: str = "es_core_news_md"):
    try:
        import spacy

        try:
            nlp = spacy.load(model_name)
        except OSError:
            logger.info("spaCy model '%s' not found — downloading…", model_name)
            import spacy.cli

            spacy.cli.download(model_name)
            nlp = spacy.load(model_name)
        logger.info("spaCy model '%s' loaded.", model_name)
        return nlp
    except Exception as e:
        logger.warning("Could not load spaCy model '%s': %s", model_name, e)
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_useful_noun(lemma: str) -> bool:
    return lemma not in GENERIC_NOUNS and len(lemma) >= _MIN_LEMMA_LEN


def _clean_chunk(span) -> str | None:
    """Return a cleaned noun-chunk string keeping only NOUN/PROPN/ADJ tokens."""
    parts = [
        t.lemma_.lower()
        for t in span
        if t.pos_ in ("NOUN", "PROPN", "ADJ") and _is_useful_noun(t.lemma_.lower())
    ]
    return " ".join(parts) if parts else None


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------


def extract_anchors(text: str, model_name: str = "es_core_news_md") -> dict[str, Any]:
    nlp = _load_spacy_model(model_name)
    if nlp is None:
        logger.warning("NLP engine unavailable — returning empty anchors.")
        return _empty_anchors()

    doc = nlp(text)

    domain_nouns: set[str] = set()
    action_verbs: set[str] = set()
    potential_commands: set[str] = set()
    actors: set[str] = set()

    # --- Token-level pass: verbs, actors, single nouns ---
    for token in doc:
        # 1. Action verbs (filtered)
        if (
            token.pos_ == "VERB"
            and token.lemma_.lower() not in GENERIC_VERBS
            and len(token.lemma_) >= _MIN_LEMMA_LEN
        ):
            action_verbs.add(token.lemma_.lower())

            # Verb + direct-object → potential Command (e.g. "Aprobar solicitud")
            for child in token.children:
                if child.dep_ == "obj" and child.pos_ in ("NOUN", "PROPN"):
                    obj_lemma = child.lemma_.lower()
                    if _is_useful_noun(obj_lemma):
                        command = f"{token.lemma_.capitalize()} {obj_lemma}"
                        potential_commands.add(command)

        # 2. Single nouns (candidates for Aggregates / Entities)
        if token.pos_ in ("NOUN", "PROPN"):
            lemma = token.lemma_.lower()
            if _is_useful_noun(lemma):
                domain_nouns.add(lemma)

            # Nominal subjects → Actor candidates
            if token.dep_ == "nsubj":
                actors.add(token.text.capitalize())

    # --- Chunk-level pass: compound domain terms ("entidad raíz") ---
    for chunk in doc.noun_chunks:
        if len(chunk) >= 2:
            cleaned = _clean_chunk(chunk)
            if cleaned and " " in cleaned:
                domain_nouns.add(cleaned)

    # --- Named Entities (exclude LOC — locations rarely map to DDD concepts) ---
    entities: list[dict[str, str]] = []
    seen_entities: set[tuple[str, str]] = set()
    for ent in doc.ents:
        key = (ent.text.strip().lower(), ent.label_)
        if key not in seen_entities and ent.label_ not in ("LOC",):
            seen_entities.add(key)
            entities.append({"text": ent.text.strip(), "label": ent.label_})

    return {
        "actors": sorted(actors),
        "domain_terms": sorted(domain_nouns),
        "potential_commands": sorted(potential_commands),
        "action_verbs": sorted(action_verbs),
        "entities": sorted(entities, key=lambda e: (e["label"], e["text"].lower())),
    }

def is_available(model_name: str = "es_core_news_md") -> bool:
    return _load_spacy_model(model_name) is not None


# ---------------------------------------------------------------------------
# Prompt injection — maps anchors to DDD/Event-Storming taxonomy
# ---------------------------------------------------------------------------


def inject_anchors_to_prompt(anchors: dict[str, Any], base_prompt: str) -> str:
    if not anchors or not any(anchors.values()):
        return base_prompt

    anchor_lines = [
        "<anchors>",
        "The following elements were deterministically extracted from the domain expert's transcript.",
        "You MUST map these terms to DDD concepts. Do NOT invent new root aggregates or actions",
        "if they are not derived from this list.\n",
    ]

    if anchors.get("actors"):
        anchor_lines.append(
            "POTENTIAL ACTORS (Map to tipo_elemento='Actor' or 'Sistema Externo'):"
        )
        for actor in anchors["actors"]:
            anchor_lines.append(f"  - {actor}")

    if anchors.get("domain_terms"):
        anchor_lines.append(
            "\nCORE DOMAIN TERMS (Candidates for 'Agregado', 'Entidad Raíz', Value Objects):"
        )
        for term in anchors["domain_terms"]:
            anchor_lines.append(f"  - {term}")

    if anchors.get("potential_commands"):
        anchor_lines.append(
            "\nPOTENTIAL COMMANDS (Map to tipo_elemento='Comando' — use VerbNoun naming):"
        )
        for cmd in anchors["potential_commands"]:
            anchor_lines.append(f"  - {cmd}")

    if anchors.get("action_verbs"):
        anchor_lines.append(
            "\nACTION VERBS (Derive 'Evento' as NounPastParticiple from these):"
        )
        for verb in anchors["action_verbs"]:
            anchor_lines.append(f"  - {verb}")

    if anchors.get("entities"):
        anchor_lines.append(
            "\nNAMED ENTITIES (Likely 'Sistema Externo' or 'Actor' — verify role):"
        )
        for ent in anchors["entities"]:
            anchor_lines.append(f"  - {ent['text']} ({ent['label']})")

    anchor_lines.append("</anchors>\n")
    return "\n".join(anchor_lines) + "\n" + base_prompt


def _empty_anchors() -> dict[str, Any]:
    return {
        "actors": [],
        "domain_terms": [],
        "potential_commands": [],
        "action_verbs": [],
        "entities": [],
    }