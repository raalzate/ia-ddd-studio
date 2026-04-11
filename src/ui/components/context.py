import streamlit as st


def render_context_fields(key_suffix: str = "main"):
    """Renderiza los campos de contexto adicional (sin expander externo)."""
    st.markdown("Sube documentación oficial para que la IA contraste la transcripción con la realidad.")
    col1, col2 = st.columns(2)
    with col1:
        pdf = st.file_uploader("Subir PDF de referencia", type=["pdf"], key=f"ctx_pdf_{key_suffix}")
    with col2:
        text = st.text_area("O pegar reglas manuales", height=100, key=f"ctx_text_{key_suffix}")
    return pdf, text
