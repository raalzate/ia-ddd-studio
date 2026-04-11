"""Extended tests for results.py — _render_data_tab."""

from unittest.mock import MagicMock, patch

import pandas as pd


class _SessionState(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        del self[key]


@patch("ui.components.results.save_static_json")
@patch("ui.components.results.reconstruct_domain_analysis")
@patch("ui.components.results.analyze_domain_data")
@patch("ui.components.results.st")
def test_render_data_tab_displays_editors(mock_st, mock_analyze, mock_recon, mock_save, sample_domain_analysis):
    from ui.components.results import _render_data_tab

    mock_analyze.return_value = {
        "nodes_bp_df": pd.DataFrame([{"id": "n1", "tipo_elemento": "Evento"}]),
        "edges_bp_df": pd.DataFrame(),
        "nodes_agg_df": pd.DataFrame(),
        "edges_agg_df": pd.DataFrame(),
        "policies_df": pd.DataFrame(),
        "read_models_df": pd.DataFrame(),
    }

    mock_st.expander.return_value.__enter__ = MagicMock()
    mock_st.expander.return_value.__exit__ = MagicMock()

    mock_c1 = MagicMock()
    mock_c2 = MagicMock()
    mock_st.columns.return_value = (mock_c1, mock_c2)
    mock_c1.data_editor.return_value = pd.DataFrame()
    mock_c2.data_editor.return_value = pd.DataFrame()
    mock_st.data_editor.return_value = pd.DataFrame()
    mock_st.button.return_value = False

    _render_data_tab(sample_domain_analysis, sample_domain_analysis.model_dump())

    # Should have called expanders and data editors
    assert mock_st.expander.call_count >= 3


@patch("ui.components.results.render_chat_tab")
@patch("ui.components.results.render_graph_tab")
@patch("ui.components.results.render_specs_tab")
@patch("ui.components.results.render_stats_tab")
@patch("ui.components.results.st")
def test_render_results_tabs_valid_result(
    mock_st, mock_stats, mock_specs, mock_graph, mock_chat, sample_domain_analysis
):
    from ui.components.results import render_results_tabs

    mock_st.session_state = _SessionState({"logs": "test"})

    mock_c1, mock_c2, mock_c3, mock_c4 = MagicMock(), MagicMock(), MagicMock(), MagicMock()
    mock_st.columns.return_value = (mock_c1, mock_c2, mock_c3, mock_c4)

    tabs = [MagicMock() for _ in range(6)]
    for t in tabs:
        t.__enter__ = MagicMock()
        t.__exit__ = MagicMock()
    mock_st.tabs.return_value = tabs

    # Mock _render_data_tab to avoid deep mock chains
    with patch("ui.components.results._render_data_tab"):
        result = {
            "analysis": sample_domain_analysis,
            "transcript": "test transcript",
            "specs": {"context_map": "some puml"},
        }
        render_results_tabs(result)

    mock_st.divider.assert_called()
