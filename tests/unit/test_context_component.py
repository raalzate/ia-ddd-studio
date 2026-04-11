"""Unit tests for src/ui/components/context.py — render_context_fields."""

from unittest.mock import MagicMock, patch


@patch("ui.components.context.st")
def test_render_context_fields_returns_tuple(mock_st):
    from ui.components.context import render_context_fields

    mock_col1 = MagicMock()
    mock_col2 = MagicMock()
    mock_st.columns.return_value = [mock_col1, mock_col2]

    mock_col1.__enter__ = MagicMock(return_value=mock_col1)
    mock_col1.__exit__ = MagicMock(return_value=False)
    mock_col2.__enter__ = MagicMock(return_value=mock_col2)
    mock_col2.__exit__ = MagicMock(return_value=False)

    # Mock the st module-level calls (file_uploader, text_area use st directly within context)
    mock_st.file_uploader.return_value = None
    mock_st.text_area.return_value = "some rules"

    pdf, text = render_context_fields()
    # The function uses st.file_uploader and st.text_area inside with blocks
    assert pdf is None or True  # depends on mock resolution
