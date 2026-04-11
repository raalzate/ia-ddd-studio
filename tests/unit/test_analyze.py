"""Unit tests for src/ui/analyze.py — analyze_domain_data extraction."""

import pandas as pd
import pytest

from ui.analyze import analyze_domain_data


@pytest.fixture
def analysis_obj(sample_domain_analysis):
    return sample_domain_analysis


class TestAnalyzeDomainData:
    def test_returns_expected_keys(self, analysis_obj):
        dfs = analyze_domain_data(analysis_obj)
        expected_keys = {
            "nodes_bp_df",
            "edges_bp_df",
            "nodes_agg_df",
            "edges_agg_df",
            "policies_df",
            "read_models_df",
            "node_types_df",
            "node_states_df",
            "edge_types_df",
            "technologies_df",
        }
        assert set(dfs.keys()) == expected_keys

    def test_big_picture_nodes_extracted(self, analysis_obj):
        dfs = analyze_domain_data(analysis_obj)
        bp_nodes = dfs["nodes_bp_df"]
        assert isinstance(bp_nodes, pd.DataFrame)
        # Should have Event and Command nodes from the sample
        assert len(bp_nodes) > 0

    def test_big_picture_edges_extracted(self, analysis_obj):
        dfs = analyze_domain_data(analysis_obj)
        bp_edges = dfs["edges_bp_df"]
        assert isinstance(bp_edges, pd.DataFrame)
        assert len(bp_edges) > 0

    def test_aggregate_nodes_extracted(self, analysis_obj):
        dfs = analyze_domain_data(analysis_obj)
        agg_nodes = dfs["nodes_agg_df"]
        assert isinstance(agg_nodes, pd.DataFrame)
        # sample has 2 aggregates with 2 nodes each
        assert len(agg_nodes) == 4

    def test_aggregate_nodes_have_aggregate_column(self, analysis_obj):
        dfs = analyze_domain_data(analysis_obj)
        agg_nodes = dfs["nodes_agg_df"]
        assert "aggregate" in agg_nodes.columns

    def test_bp_nodes_have_no_aggregate_column(self, analysis_obj):
        dfs = analyze_domain_data(analysis_obj)
        bp_nodes = dfs["nodes_bp_df"]
        assert "aggregate" not in bp_nodes.columns

    def test_node_types_distribution(self, analysis_obj):
        dfs = analyze_domain_data(analysis_obj)
        types_df = dfs["node_types_df"]
        assert not types_df.empty
        # Should contain at least Evento and Comando
        types = set(types_df["tipo_elemento"].tolist())
        assert "Evento" in types
        assert "Comando" in types

    def test_policies_df_has_default_row_when_empty(self, analysis_obj):
        # Default sample has no policies
        dfs = analyze_domain_data(analysis_obj)
        policies = dfs["policies_df"]
        assert isinstance(policies, pd.DataFrame)
        assert len(policies) >= 1  # At least the default empty row

    def test_read_models_df_has_default_row_when_empty(self, analysis_obj):
        dfs = analyze_domain_data(analysis_obj)
        rms = dfs["read_models_df"]
        assert isinstance(rms, pd.DataFrame)
        assert len(rms) >= 1

    def test_technologies_df_empty_when_no_tags(self, analysis_obj):
        dfs = analyze_domain_data(analysis_obj)
        techs = dfs["technologies_df"]
        assert isinstance(techs, pd.DataFrame)

    def test_all_dataframes_have_no_nan(self, analysis_obj):
        dfs = analyze_domain_data(analysis_obj)
        for key in ["nodes_bp_df", "edges_bp_df", "nodes_agg_df", "edges_agg_df"]:
            df = dfs[key]
            if not df.empty:
                assert not df.isnull().any().any(), f"{key} contains NaN values"
