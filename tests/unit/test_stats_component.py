"""Unit tests for src/ui/visualization/stats.py — render_stats_tab."""

from unittest.mock import MagicMock, patch


@patch("ui.visualization.stats.analyze_domain_data")
@patch("ui.visualization.stats.st")
def test_render_stats_tab_runs_without_error(mock_st, mock_analyze, sample_domain_analysis):
    import pandas as pd
    from ui.visualization.stats import render_stats_tab

    # Mock analyze_domain_data to return expected DataFrames
    mock_analyze.return_value = {
        "node_types_df": pd.DataFrame([{"tipo_elemento": "Evento", "count": 4}]),
        "technologies_df": pd.DataFrame(columns=["technology"]),
    }

    mock_col1 = MagicMock()
    mock_col2 = MagicMock()
    mock_st.columns.return_value = (mock_col1, mock_col2)

    render_stats_tab(sample_domain_analysis)

    mock_st.subheader.assert_called_once()


@patch("ui.visualization.stats.analyze_domain_data")
@patch("ui.visualization.stats.st")
def test_render_stats_tab_handles_empty_data(mock_st, mock_analyze, sample_domain_analysis):
    import pandas as pd
    from ui.visualization.stats import render_stats_tab

    mock_analyze.return_value = {
        "node_types_df": pd.DataFrame(columns=["tipo_elemento", "count"]),
        "technologies_df": pd.DataFrame(columns=["technology"]),
    }

    mock_col1 = MagicMock()
    mock_col2 = MagicMock()
    mock_st.columns.return_value = (mock_col1, mock_col2)

    render_stats_tab(sample_domain_analysis)
    mock_st.subheader.assert_called_once()
