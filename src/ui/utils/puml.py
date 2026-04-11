"""Render PlantUML diagrams in Streamlit via Kroki API."""

import base64
import zlib

import requests
import streamlit as st
import streamlit.components.v1 as components

_KROKI_URL = "https://kroki.io/plantuml/svg/{}"


def _encode_kroki(puml_text: str) -> str:
    compressed = zlib.compress(puml_text.encode("utf-8"), level=9)
    return base64.urlsafe_b64encode(compressed).decode("utf-8")


def _clean_puml(raw: str) -> str:
    """Strip markdown fences so only PlantUML syntax remains."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def render_plantuml(puml_text: str, height: int = 650) -> None:
    """Render a PlantUML diagram using the Kroki API.

    Falls back to showing raw code if the request fails.
    """
    clean = _clean_puml(puml_text)
    encoded = _encode_kroki(clean)
    url = _KROKI_URL.format(encoded)
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            svg = resp.text
            components.html(
                f'<div style="overflow:auto;padding:8px;">{svg}</div>',
                height=height,
                scrolling=True,
            )
            return
    except Exception:
        pass

    st.warning("No se pudo renderizar el diagrama. Mostrando código PlantUML.")
    st.code(clean, language="text")
