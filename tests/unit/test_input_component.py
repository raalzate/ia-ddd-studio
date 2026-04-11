"""Unit tests for src/ui/components/input.py — helper functions."""

from unittest.mock import MagicMock, patch


@patch("ui.components.input.st")
def test_get_draft_service_creates_singleton(mock_st):
    from ui.components.input import _get_draft_service

    mock_st.session_state = {}
    service = _get_draft_service()
    assert service is not None
    assert "_draft_service" in mock_st.session_state


@patch("ui.components.input.st")
def test_get_draft_service_returns_existing(mock_st):
    from ui.components.input import _get_draft_service

    sentinel = object()
    mock_st.session_state = {"_draft_service": sentinel}
    service = _get_draft_service()
    assert service is sentinel


@patch("ui.components.input.st")
def test_pdf_to_markdown_delegates(mock_st):
    from ui.components.input import _pdf_to_markdown

    with patch("ui.utils.pdf.pymupdf4llm") as mock_4llm, patch("ui.utils.pdf.pymupdf") as mock_pymupdf:
        mock_uploaded = MagicMock()
        mock_uploaded.read.return_value = b"fake"
        mock_pymupdf.open.return_value = MagicMock()
        mock_4llm.to_markdown.return_value = "# Title"

        result = _pdf_to_markdown(mock_uploaded, inference=MagicMock())
        assert result == "# Title"
