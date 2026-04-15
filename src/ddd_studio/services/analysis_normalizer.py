"""Deterministic post-processing for DomainAnalysis.

After the LLM produces a DomainAnalysis, this module rewrites it to a canonical
form so that small variations across runs collapse into the same output:

  - IDs are recomputed from (level, type, name) using a strict slug rule.
  - Nodes are deduplicated by accent-insensitive lowercased name.
  - Lists are reordered by first appearance in the transcript.
  - Edges are rewritten to use the new IDs and deduped.
  - nombre_proyecto is repaired if it looks like a malformed ID.

This is pure Python — no LLM calls — so it is deterministic by construction.
"""

from __future__ import annotations

import re
import unicodedata

from models.domain_analysis import AristaGrafo, DomainAnalysis, NodoGrafo

# Map ElementType -> short code for canonical IDs.
_TYPE_TO_CODE: dict[str, str] = {
    "Actor": "ACT",
    "Sistema Externo": "SYS",
    "Hotspot": "HOT",
    "Comando": "CMD",
    "Evento": "EVT",
    "Política": "POL",
    "Política de UI": "POL",
    "Entidad Raíz": "AGG",
    "Agregado": "AGG",
    "Read Model": "RM",
    "Vista": "RM",
    "Proyección": "RM",
    "Regla de Negocio": "HOT",
}

_LEVEL_TO_PREFIX: dict[str, str] = {
    "big_picture": "BP",
    "process_level": "AGG",
    "read_model": "BC",
}


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def _pascal_case(text: str) -> str:
    """Convert arbitrary text to PascalCase, accent-free, alnum-only.

    Preserves existing camelCase boundaries: "AsignarPaquete" stays
    "AsignarPaquete" instead of collapsing to "Asignarpaquete".
    """
    cleaned = _strip_accents(text or "")
    # Insert a space at lower→Upper transitions so they become word boundaries.
    cleaned = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", cleaned)
    parts = re.split(r"[^A-Za-z0-9]+", cleaned)
    pascal = "".join(p[:1].upper() + p[1:].lower() for p in parts if p)
    return pascal or "X"


def canonical_id(level: str, tipo: str, nombre: str) -> str:
    """Build a deterministic ID of the form `<LEVEL>-<TYPE>-<NombrePascal>`."""
    prefix = _LEVEL_TO_PREFIX.get(level, "BP")
    code = _TYPE_TO_CODE.get(tipo, "ACT")
    name_pascal = _pascal_case(nombre)
    return f"{prefix}-{code}-{name_pascal}"


def _name_key(nombre: str) -> str:
    return _strip_accents(nombre or "").lower().strip()


def _appearance_index(needle: str, haystack_lower_noaccents: str) -> int:
    """Index of first appearance of `needle` in pre-normalized haystack.

    Returns a large number if not found, so unmatched items sort last
    while preserving relative order via Python's stable sort.
    """
    nn = _strip_accents(needle or "").lower().strip()
    if not nn:
        return 10**9
    idx = haystack_lower_noaccents.find(nn)
    return idx if idx >= 0 else 10**9


def _rewrite_nodes(
    nodes: list[NodoGrafo],
    transcript_norm: str,
    id_map: dict[str, str],
) -> list[NodoGrafo]:
    """Canonicalize IDs, dedupe by name, sort by transcript order."""
    seen: dict[str, NodoGrafo] = {}
    for n in nodes:
        new_id = canonical_id(n.nivel, n.tipo_elemento, n.nombre)
        # Record old -> new even if we drop the duplicate, so edges still rewire.
        id_map[n.id] = new_id
        n.id = new_id
        key = _name_key(n.nombre)
        if not key:
            continue
        existing = seen.get(key)
        if existing is None:
            seen[key] = n
            continue
        # Merge: prefer richer metadata.
        if n.tags_tecnologia and not existing.tags_tecnologia:
            existing.tags_tecnologia = n.tags_tecnologia
        if len(n.descripcion or "") > len(existing.descripcion or ""):
            existing.descripcion = n.descripcion
    return sorted(seen.values(), key=lambda x: _appearance_index(x.nombre, transcript_norm))


def _rewrite_edges(edges: list[AristaGrafo], id_map: dict[str, str]) -> list[AristaGrafo]:
    out: list[AristaGrafo] = []
    seen_pairs: set[tuple[str, str, str]] = set()
    for e in edges:
        e.fuente = id_map.get(e.fuente, e.fuente)
        e.destino = id_map.get(e.destino, e.destino)
        key = (e.fuente, e.destino, (e.descripcion or "").strip().lower())
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        out.append(e)
    return out


# --- Project name repair --------------------------------------------------

_PASCAL_RE = re.compile(r"^[A-Z][a-z]+(?:[A-Z][a-z]+)+$")
_ALL_CAPS_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,}$")
_TITLE_NO_ACCENT_RE = re.compile(r"^(?:[A-Z][a-z]+\s){2,}[A-Z][a-z]+$")


def _looks_malformed_project_name(name: str) -> bool:
    if not name or not name.strip():
        return True
    s = name.strip()
    if s.startswith("(") and s.endswith(")"):
        return True
    if _PASCAL_RE.match(s):
        return True
    if _ALL_CAPS_RE.match(s):
        return True
    return False


_PROJECT_NAME_PATTERNS = [
    r"digitaliza\w*\s+(?:de\s+)?(?:la\s+|el\s+)?[\w\sáéíóúñ]{3,80}",
    r"sistema\s+de\s+[\w\sáéíóúñ]{3,60}",
    r"plataforma\s+de\s+[\w\sáéíóúñ]{3,60}",
    r"gesti[oó]n\s+de\s+[\w\sáéíóúñ]{3,60}",
    r"onboarding\s+(?:de\s+)?[\w\sáéíóúñ]{3,60}",
]


def _extract_project_name_from_transcript(transcript: str) -> str | None:
    if not transcript:
        return None
    low = transcript.lower()
    for pat in _PROJECT_NAME_PATTERNS:
        m = re.search(pat, low)
        if m:
            phrase = m.group(0)
            phrase = re.split(r"[.,;:\n¿?¡!]", phrase)[0].strip()
            if 5 <= len(phrase) <= 80:
                return phrase[0].upper() + phrase[1:]
    return None


def repair_project_name(current: str, transcript: str) -> str:
    if not _looks_malformed_project_name(current):
        return current.strip()
    extracted = _extract_project_name_from_transcript(transcript)
    if extracted:
        return extracted
    return (current or "").strip() or "Proyecto sin nombre"


# --- Public entry point ---------------------------------------------------


def normalize_analysis(analysis: DomainAnalysis, transcript: str) -> DomainAnalysis:
    """Apply all normalization rules to `analysis`. Mutates and returns it."""
    transcript_norm = _strip_accents(transcript or "").lower()
    id_map: dict[str, str] = {}

    analysis.big_picture.nodos = _rewrite_nodes(analysis.big_picture.nodos, transcript_norm, id_map)
    for agg in analysis.agregados:
        agg.nodos = _rewrite_nodes(agg.nodos, transcript_norm, id_map)

    analysis.big_picture.aristas = _rewrite_edges(analysis.big_picture.aristas, id_map)
    for agg in analysis.agregados:
        agg.aristas = _rewrite_edges(agg.aristas, id_map)
    analysis.politicas_inter_agregados = _rewrite_edges(analysis.politicas_inter_agregados, id_map)

    # Read models reference event IDs in `proyecta` — rewire them too.
    for rm in analysis.read_models:
        rm.proyecta = [id_map.get(eid, eid) for eid in rm.proyecta]

    analysis.nombre_proyecto = repair_project_name(analysis.nombre_proyecto, transcript)
    return analysis
