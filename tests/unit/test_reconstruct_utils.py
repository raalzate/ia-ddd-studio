"""Unit tests for src/ui/reconstruct_utils.py — DataFrame-to-dict reconstruction."""

import pandas as pd
from ui.reconstruct_utils import (
    _process_nodes_list,
    _reconstruct_big_picture,
    _reconstruct_inter_aggregate_policies,
    _reconstruct_read_models,
    reconstruct_domain_analysis,
)


class TestProcessNodesList:
    def test_sets_default_nivel_when_missing(self):
        nodes = [{"nombre": "A", "tags_tecnologia": []}]
        result = _process_nodes_list(nodes, "big_picture")
        assert result[0]["nivel"] == "big_picture"

    def test_sets_default_nivel_when_empty_string(self):
        nodes = [{"nombre": "A", "nivel": "", "tags_tecnologia": []}]
        result = _process_nodes_list(nodes, "process_level")
        assert result[0]["nivel"] == "process_level"

    def test_preserves_existing_nivel(self):
        nodes = [{"nombre": "A", "nivel": "big_picture", "tags_tecnologia": []}]
        result = _process_nodes_list(nodes, "process_level")
        assert result[0]["nivel"] == "big_picture"

    def test_converts_string_tags_to_list(self):
        nodes = [{"nombre": "A", "nivel": "bp", "tags_tecnologia": "java, python, go"}]
        result = _process_nodes_list(nodes, "bp")
        assert result[0]["tags_tecnologia"] == ["java", "python", "go"]

    def test_converts_none_string_tags_to_empty_list(self):
        nodes = [{"nombre": "A", "nivel": "bp", "tags_tecnologia": "None"}]
        result = _process_nodes_list(nodes, "bp")
        assert result[0]["tags_tecnologia"] == []

    def test_converts_empty_string_tags_to_empty_list(self):
        nodes = [{"nombre": "A", "nivel": "bp", "tags_tecnologia": ""}]
        result = _process_nodes_list(nodes, "bp")
        assert result[0]["tags_tecnologia"] == []

    def test_converts_nan_string_tags_to_empty_list(self):
        nodes = [{"nombre": "A", "nivel": "bp", "tags_tecnologia": "nan"}]
        result = _process_nodes_list(nodes, "bp")
        assert result[0]["tags_tecnologia"] == []

    def test_keeps_list_tags_unchanged(self):
        nodes = [{"nombre": "A", "nivel": "bp", "tags_tecnologia": ["java"]}]
        result = _process_nodes_list(nodes, "bp")
        assert result[0]["tags_tecnologia"] == ["java"]

    def test_converts_non_list_non_string_to_empty_list(self):
        nodes = [{"nombre": "A", "nivel": "bp", "tags_tecnologia": 42}]
        result = _process_nodes_list(nodes, "bp")
        assert result[0]["tags_tecnologia"] == []


class TestReconstructBigPicture:
    def test_reconstructs_nodes_and_edges(self):
        modified = {"big_picture": {"nodos": [], "aristas": []}}
        nodes_df = pd.DataFrame(
            [{"id": "n1", "tipo_elemento": "Evento", "nombre": "E1", "tags_tecnologia": [], "nivel": "big_picture"}]
        )
        edges_df = pd.DataFrame([{"fuente": "n1", "destino": "n2", "descripcion": "triggers"}])
        _reconstruct_big_picture(modified, nodes_df, edges_df)
        assert len(modified["big_picture"]["nodos"]) == 1
        assert len(modified["big_picture"]["aristas"]) == 1

    def test_handles_empty_dataframes(self):
        modified = {"big_picture": {"nodos": [], "aristas": []}}
        _reconstruct_big_picture(modified, pd.DataFrame(), pd.DataFrame())
        assert modified["big_picture"]["nodos"] == []
        assert modified["big_picture"]["aristas"] == []


class TestReconstructInterAggregatePolicies:
    def test_sets_policies_from_dataframe(self):
        modified = {"politicas_inter_agregados": []}
        df = pd.DataFrame([{"fuente": "a", "destino": "b", "descripcion": "policy"}])
        _reconstruct_inter_aggregate_policies(modified, df)
        assert len(modified["politicas_inter_agregados"]) == 1

    def test_handles_empty_dataframe(self):
        modified = {"politicas_inter_agregados": ["old"]}
        _reconstruct_inter_aggregate_policies(modified, pd.DataFrame())
        assert modified["politicas_inter_agregados"] == []


class TestReconstructReadModels:
    def test_rebuilds_read_models(self):
        modified = {"read_models": []}
        df = pd.DataFrame(
            [
                {
                    "nombre": "Dashboard",
                    "descripcion": "Shows orders",
                    "proyecta": "evt1, evt2",
                    "ui_policies": "policy1; policy2",
                    "tecnologias": "React, Redux",
                }
            ]
        )
        _reconstruct_read_models(modified, df)
        assert len(modified["read_models"]) == 1
        rm = modified["read_models"][0]
        assert rm["nombre"] == "Dashboard"
        assert rm["proyecta"] == ["evt1", "evt2"]
        assert rm["ui_policies"] == ["policy1", "policy2"]
        assert rm["tecnologias"] == ["React", "Redux"]

    def test_filters_out_nan_names(self):
        modified = {"read_models": []}
        df = pd.DataFrame([{"nombre": "nan", "descripcion": "", "proyecta": "", "ui_policies": "", "tecnologias": ""}])
        _reconstruct_read_models(modified, df)
        assert len(modified["read_models"]) == 0

    def test_filters_out_empty_names(self):
        modified = {"read_models": []}
        df = pd.DataFrame([{"nombre": "", "descripcion": "", "proyecta": "", "ui_policies": "", "tecnologias": ""}])
        _reconstruct_read_models(modified, df)
        assert len(modified["read_models"]) == 0


class TestReconstructDomainAnalysis:
    def _make_original(self):
        return {
            "big_picture": {"nodos": [], "aristas": []},
            "agregados": [],
            "politicas_inter_agregados": [],
            "read_models": [],
        }

    def test_full_reconstruction(self):
        original = self._make_original()
        result = reconstruct_domain_analysis(
            original,
            nodes_bp_df=pd.DataFrame(),
            edges_bp_df=pd.DataFrame(),
            nodes_agg_df=pd.DataFrame(),
            edges_agg_df=pd.DataFrame(),
            policies_df=pd.DataFrame(),
            read_models_df=pd.DataFrame(),
        )
        assert "big_picture" in result
        assert "agregados" in result
        assert "politicas_inter_agregados" in result
        assert "read_models" in result

    def test_does_not_mutate_original(self):
        original = self._make_original()
        original["politicas_inter_agregados"] = [{"fuente": "a", "destino": "b"}]
        reconstruct_domain_analysis(
            original,
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
        )
        assert len(original["politicas_inter_agregados"]) == 1  # not mutated
