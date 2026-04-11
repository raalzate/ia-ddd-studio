"""Unit tests for src/ui/utils/puml.py — PlantUML encoding and rendering."""

from unittest.mock import MagicMock, patch


def test_encode_kroki_returns_base64():
    from ui.utils.puml import _encode_kroki

    result = _encode_kroki("@startuml\nA -> B\n@enduml")
    assert isinstance(result, str)
    assert len(result) > 0


def test_clean_puml_strips_markdown_fences():
    from ui.utils.puml import _clean_puml

    raw = "```plantuml\n@startuml\nA -> B\n@enduml\n```"
    result = _clean_puml(raw)
    assert result.startswith("@startuml")
    assert result.endswith("@enduml")
    assert "```" not in result


def test_clean_puml_no_fences():
    from ui.utils.puml import _clean_puml

    raw = "@startuml\nA -> B\n@enduml"
    result = _clean_puml(raw)
    assert result == raw.strip()


def test_clean_puml_empty():
    from ui.utils.puml import _clean_puml

    assert _clean_puml("") == ""


def test_clean_puml_only_backticks():
    from ui.utils.puml import _clean_puml

    result = _clean_puml("```\n```")
    assert "```" not in result


@patch("ui.utils.puml.requests")
@patch("ui.utils.puml.components")
def test_render_plantuml_success(mock_components, mock_requests):
    from ui.utils.puml import render_plantuml

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<svg>diagram</svg>"
    mock_requests.get.return_value = mock_response

    render_plantuml("@startuml\nA -> B\n@enduml", height=700)

    mock_requests.get.assert_called_once()
    mock_components.html.assert_called_once()
    html_arg = mock_components.html.call_args[0][0]
    assert "<svg>diagram</svg>" in html_arg


@patch("ui.utils.puml.st")
@patch("ui.utils.puml.requests")
def test_render_plantuml_fallback_on_error(mock_requests, mock_st):
    from ui.utils.puml import render_plantuml

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_requests.get.return_value = mock_response

    render_plantuml("@startuml\nA -> B\n@enduml")

    mock_st.warning.assert_called_once()
    mock_st.code.assert_called_once()


@patch("ui.utils.puml.st")
@patch("ui.utils.puml.requests")
def test_render_plantuml_fallback_on_exception(mock_requests, mock_st):
    from ui.utils.puml import render_plantuml

    mock_requests.get.side_effect = ConnectionError("network error")

    render_plantuml("@startuml\nA -> B\n@enduml")

    mock_st.warning.assert_called_once()
