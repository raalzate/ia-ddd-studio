"""Unit tests for src/ui/utils/mermaid.py — sanitize_mermaid and render_mermaid."""

from unittest.mock import patch


def test_sanitize_mermaid_quotes_subgraph_labels():
    from ui.utils.mermaid import sanitize_mermaid

    code = "subgraph Order Processing"
    result = sanitize_mermaid(code)
    assert '"Order Processing"' in result


def test_sanitize_mermaid_leaves_already_quoted_labels():
    from ui.utils.mermaid import sanitize_mermaid

    code = 'subgraph "Already Quoted"'
    result = sanitize_mermaid(code)
    assert result.strip() == 'subgraph "Already Quoted"'


def test_sanitize_mermaid_preserves_non_subgraph_lines():
    from ui.utils.mermaid import sanitize_mermaid

    code = "A --> B\nC --> D"
    result = sanitize_mermaid(code)
    assert result == code


def test_sanitize_mermaid_multiline():
    from ui.utils.mermaid import sanitize_mermaid

    code = "graph TD\nsubgraph Payment Gateway\n  A --> B\nend"
    result = sanitize_mermaid(code)
    assert '"Payment Gateway"' in result
    assert "A --> B" in result


def test_sanitize_mermaid_empty_input():
    from ui.utils.mermaid import sanitize_mermaid

    assert sanitize_mermaid("") == ""


@patch("ui.utils.mermaid.components")
def test_render_mermaid_calls_components_html(mock_components):
    from ui.utils.mermaid import render_mermaid

    render_mermaid("graph TD\nA --> B", height=500)
    mock_components.html.assert_called_once()
    call_args = mock_components.html.call_args
    assert call_args[1]["height"] == 500
    assert call_args[1]["scrolling"] is True
    html_content = call_args[0][0]
    assert "mermaid" in html_content
    assert "A --> B" in html_content


@patch("ui.utils.mermaid.components")
def test_render_mermaid_escapes_js_special_chars(mock_components):
    from ui.utils.mermaid import render_mermaid

    render_mermaid("A --> B\\nC`D${E}", height=600)
    html_content = mock_components.html.call_args[0][0]
    # Ensure backticks and template literals are escaped
    assert "\\`" in html_content
    assert "\\${" in html_content
