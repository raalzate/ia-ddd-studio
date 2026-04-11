import json
import os
from typing import Any

STATIC_DIR = "static"
STATIC_JSON_PATH = os.path.join(STATIC_DIR, "domain_analysis.json")
LLM_CONFIG_PATH = os.path.join(STATIC_DIR, "llm_config.json")


def save_static_json(data: dict):
    """Guarda el JSON en disco para persistencia."""
    os.makedirs(STATIC_DIR, exist_ok=True)
    with open(STATIC_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_static_json() -> dict[str, Any]:
    """Carga el JSON persistido si existe."""
    if os.path.exists(STATIC_JSON_PATH):
        try:
            with open(STATIC_JSON_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_llm_config(config: dict) -> None:
    """Persist LLM configuration to disk."""
    os.makedirs(STATIC_DIR, exist_ok=True)
    with open(LLM_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def load_llm_config() -> dict | None:
    """Load persisted LLM configuration from disk, or None if not found."""
    if os.path.exists(LLM_CONFIG_PATH):
        try:
            with open(LLM_CONFIG_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def clear_static_json():
    """Elimina el archivo JSON estático."""
    if os.path.exists(STATIC_JSON_PATH):
        os.remove(STATIC_JSON_PATH)


# ── Drafts directory management ──────────────────────────────────────────

DRAFTS_DIR = os.path.join(os.path.dirname(STATIC_DIR), "drafts")


def ensure_drafts_dir(drafts_dir: str | None = None) -> str:
    """Ensure the drafts directory exists and return its path."""
    path = drafts_dir or DRAFTS_DIR
    os.makedirs(path, exist_ok=True)
    return path


def get_manifest_path(drafts_dir: str | None = None) -> str:
    """Return the path to manifest.json within the drafts directory."""
    path = drafts_dir or DRAFTS_DIR
    return os.path.join(path, "manifest.json")
