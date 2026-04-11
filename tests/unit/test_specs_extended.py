"""Extended tests for specs.py — render_specs_tab."""

from unittest.mock import MagicMock, patch


@patch("ui.components.specs.render_plantuml")
@patch("ui.components.specs.save_static_json")
@patch("ui.components.specs.st")
def test_render_specs_tab_no_specs(mock_st, mock_save, mock_puml):
    from ui.components.specs import render_specs_tab

    analysis = MagicMock()
    analysis.ddd_specs = None

    mock_st.tabs.return_value = [MagicMock(), MagicMock()]
    for tab in mock_st.tabs.return_value:
        tab.__enter__ = MagicMock()
        tab.__exit__ = MagicMock()

    mock_st.session_state = {"_inference_port": MagicMock()}
    mock_st.button.return_value = False
    mock_st.expander.return_value.__enter__ = MagicMock()
    mock_st.expander.return_value.__exit__ = MagicMock()

    render_specs_tab(analysis)

    # Should set ddd_specs to empty dict
    assert analysis.ddd_specs == {}


@patch("ui.components.specs.render_plantuml")
@patch("ui.components.specs.save_static_json")
@patch("ui.components.specs.st")
def test_render_specs_tab_with_context_map(mock_st, mock_save, mock_puml):
    from ui.components.specs import render_specs_tab

    analysis = MagicMock()
    analysis.ddd_specs = {"context_map": "@startuml\nA -> B\n@enduml"}
    analysis.model_dump.return_value = {}

    mock_st.tabs.return_value = [MagicMock(), MagicMock()]
    for tab in mock_st.tabs.return_value:
        tab.__enter__ = MagicMock()
        tab.__exit__ = MagicMock()

    mock_st.session_state = {"_inference_port": MagicMock()}
    mock_st.button.return_value = False
    mock_st.expander.return_value.__enter__ = MagicMock()
    mock_st.expander.return_value.__exit__ = MagicMock()
    mock_st.text_area.return_value = "@startuml\nA -> B\n@enduml"

    render_specs_tab(analysis)

    mock_puml.assert_called()


@patch("ui.components.specs.render_plantuml")
@patch("ui.components.specs.save_static_json")
@patch("ui.components.specs.st")
def test_render_specs_tab_generate_button(mock_st, mock_save, mock_puml):
    from ui.components.specs import render_specs_tab

    analysis = MagicMock()
    analysis.ddd_specs = {}
    analysis.model_dump.return_value = {}

    mock_st.tabs.return_value = [MagicMock(), MagicMock()]
    for tab in mock_st.tabs.return_value:
        tab.__enter__ = MagicMock()
        tab.__exit__ = MagicMock()

    mock_inference = MagicMock()
    mock_st.session_state = {"_inference_port": mock_inference}
    # First button call (generate) returns True, others False
    mock_st.button.side_effect = [True, False]
    mock_st.spinner.return_value.__enter__ = MagicMock()
    mock_st.spinner.return_value.__exit__ = MagicMock()
    mock_st.expander.return_value.__enter__ = MagicMock()
    mock_st.expander.return_value.__exit__ = MagicMock()

    with patch("ui.components.specs.SpecGenerator") as mock_gen_cls:
        mock_gen = MagicMock()
        mock_gen.generate_context_map.return_value = "@startuml\nresult\n@enduml"
        mock_gen_cls.return_value = mock_gen

        render_specs_tab(analysis)

        mock_gen.generate_context_map.assert_called_once()
