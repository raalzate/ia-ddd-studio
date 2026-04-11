"""Unit tests for src/ui/utils/pdf.py — PDF to Markdown conversion."""

from unittest.mock import MagicMock, patch


@patch("ui.utils.pdf.pymupdf4llm")
@patch("ui.utils.pdf.pymupdf")
def test_pdf_to_markdown_success(mock_pymupdf, mock_pymupdf4llm):
    from ui.utils.pdf import pdf_to_markdown

    mock_uploaded = MagicMock()
    mock_uploaded.read.return_value = b"%PDF-1.4 fake content"

    mock_doc = MagicMock()
    mock_pymupdf.open.return_value = mock_doc
    mock_pymupdf4llm.to_markdown.return_value = "# Heading\n\nSome content"

    result = pdf_to_markdown(mock_uploaded)

    assert result == "# Heading\n\nSome content"
    mock_uploaded.read.assert_called_once()
    mock_pymupdf.open.assert_called_once_with(stream=b"%PDF-1.4 fake content", filetype="pdf")
    mock_pymupdf4llm.to_markdown.assert_called_once_with(mock_doc)


@patch("ui.utils.pdf.st")
@patch("ui.utils.pdf.pymupdf")
def test_pdf_to_markdown_returns_empty_on_error(mock_pymupdf, mock_st):
    from ui.utils.pdf import pdf_to_markdown

    mock_uploaded = MagicMock()
    mock_uploaded.read.side_effect = RuntimeError("read error")

    result = pdf_to_markdown(mock_uploaded)

    assert result == ""
    mock_st.error.assert_called_once()


@patch("ui.utils.pdf.pymupdf4llm")
@patch("ui.utils.pdf.pymupdf")
def test_pdf_to_markdown_ignores_inference_param(mock_pymupdf, mock_pymupdf4llm):
    from ui.utils.pdf import pdf_to_markdown

    mock_uploaded = MagicMock()
    mock_uploaded.read.return_value = b"fake"
    mock_pymupdf.open.return_value = MagicMock()
    mock_pymupdf4llm.to_markdown.return_value = "text"

    # inference param is accepted but ignored
    result = pdf_to_markdown(mock_uploaded, inference="should_be_ignored")
    assert result == "text"
