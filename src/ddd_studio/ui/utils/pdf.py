import pymupdf
import pymupdf4llm
import streamlit as st


def pdf_to_markdown(uploaded_file, inference=None) -> str:
    """Convert a PDF to structured Markdown deterministically using PyMuPDF.

    Uses layout analysis (font sizes, blocks, tables) to reconstruct
    headings, lists, and tables without any AI inference.
    The ``inference`` parameter is accepted for API compatibility but ignored.

    Args:
        uploaded_file: Streamlit UploadedFile object.
        inference: Unused. Kept for backwards-compatibility.

    Returns:
        Markdown string preserving all document structure and content.
    """
    try:
        pdf_bytes = uploaded_file.read()
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        md_text = pymupdf4llm.to_markdown(doc)
        return md_text
    except Exception as e:
        st.error(f"Error al procesar el PDF: {e}")
        return ""
