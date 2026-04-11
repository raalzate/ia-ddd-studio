"""Unit tests for src/ui/components/results.py — render_results_tabs and helpers."""

from unittest.mock import MagicMock, patch


@patch("ui.components.results.st")
def test_render_results_tabs_error_result(mock_st):
    from ui.components.results import render_results_tabs

    render_results_tabs({"error": "Something failed"})
    mock_st.error.assert_called_once()


@patch("ui.components.results.st")
def test_render_results_tabs_missing_analysis(mock_st):
    from ui.components.results import render_results_tabs

    render_results_tabs({"some_key": "value"})
    mock_st.error.assert_called_once()


@patch("ui.components.results.st")
def test_render_summary_metrics(mock_st, sample_domain_analysis):
    from ui.components.results import _render_summary_metrics

    mock_c1, mock_c2, mock_c3, mock_c4 = MagicMock(), MagicMock(), MagicMock(), MagicMock()
    mock_st.columns.return_value = (mock_c1, mock_c2, mock_c3, mock_c4)

    _render_summary_metrics(sample_domain_analysis)

    mock_c1.metric.assert_called_once()
    mock_c2.metric.assert_called_once()
    mock_c3.metric.assert_called_once()
    mock_c4.metric.assert_called_once()
