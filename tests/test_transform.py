"""Tests pour pipeline/transform.py et les transformers."""

import pandas as pd
import pytest

from pipeline.config import get_source_by_id
from pipeline.transform import (
    apply_column_mapping,
    apply_computed_variables,
    apply_filter,
    load_raw_file,
)


# --- Tests unitaires sur les fonctions de transformation ---


def test_apply_filter_with_matching_values():
    df = pd.DataFrame({
        "id_election": ["2026_muni_t1", "2022_pres_t1", "2017_pres_t1"],
        "code_commune": ["01001", "01001", "01001"],
        "voix": [100, 200, 300],
    })
    source = {"id": "test", "filter": {"id_election": ["2026_muni_t1"]}}
    result = apply_filter(df, source)
    assert len(result) == 1
    assert result.iloc[0]["id_election"] == "2026_muni_t1"


def test_apply_filter_no_filter():
    df = pd.DataFrame({"col": [1, 2, 3]})
    source = {"id": "test"}
    result = apply_filter(df, source)
    assert len(result) == 3


def test_apply_column_mapping():
    df = pd.DataFrame({
        "CODGEO": ["01001", "01002"],
        "MED21": [20000, 25000],
        "TP6021": [10.5, 15.0],
        "EXTRA_COL": ["a", "b"],
    })
    source = {
        "id": "test",
        "join_key": "CODGEO",
        "variables": [
            {"id": "revenu_median", "source_col": "MED21"},
            {"id": "taux_pauvrete", "source_col": "TP6021"},
        ],
    }
    result = apply_column_mapping(df, source)
    assert "code_commune" in result.columns
    assert "revenu_median" in result.columns
    assert "taux_pauvrete" in result.columns
    assert "EXTRA_COL" not in result.columns
    assert len(result) == 2


def test_apply_column_mapping_missing_col():
    df = pd.DataFrame({
        "CODGEO": ["01001"],
        "MED21": [20000],
    })
    source = {
        "id": "test",
        "join_key": "CODGEO",
        "variables": [
            {"id": "revenu_median", "source_col": "MED21"},
            {"id": "missing_var", "source_col": "INEXISTANT"},
        ],
    }
    result = apply_column_mapping(df, source)
    assert "revenu_median" in result.columns
    assert "missing_var" not in result.columns


def test_apply_computed_variables():
    df = pd.DataFrame({
        "code_commune": ["01001"],
        "a": [100.0],
        "b": [200.0],
    })
    source = {
        "id": "test",
        "computed": [
            {"id": "ratio", "formula": "a / b * 100"},
        ],
    }
    result = apply_computed_variables(df, source)
    assert "ratio" in result.columns
    assert result.iloc[0]["ratio"] == pytest.approx(50.0)


def test_apply_computed_division_by_zero():
    df = pd.DataFrame({
        "code_commune": ["01001"],
        "a": [100.0],
        "b": [0.0],
    })
    source = {
        "id": "test",
        "computed": [
            {"id": "ratio", "formula": "a / b"},
        ],
    }
    result = apply_computed_variables(df, source)
    assert "ratio" in result.columns
    # Division par zéro → inf, pas d'erreur


# --- Tests sur les transformers custom (nécessitent les fichiers bruts) ---


class TestTransformersWithData:
    """Tests qui nécessitent les fichiers téléchargés dans data/raw/."""

    @pytest.fixture(autouse=True)
    def check_data_available(self):
        from pipeline.config import DATA_RAW_DIR
        if not (DATA_RAW_DIR / "loyers_2025.csv").exists():
            pytest.skip("Fichiers bruts non téléchargés")

    def test_loyers_transform(self):
        source = get_source_by_id("loyers_2025")
        df = load_raw_file(source)
        assert df is not None
        assert len(df) > 30000

    def test_elections_general_columns(self):
        from pipeline.transform import transform_source
        source = get_source_by_id("elections_agregees_general")
        if not (source and load_raw_file(source) is not None):
            pytest.skip("Données électorales non disponibles")
        df = transform_source(source)
        assert df is not None
        assert "code_commune" in df.columns
        assert any("pct_abstention" in c for c in df.columns)

    def test_elections_candidats_has_families(self):
        from pipeline.transform import transform_source
        source = get_source_by_id("elections_agregees_candidats")
        if not (source and load_raw_file(source) is not None):
            pytest.skip("Données électorales non disponibles")
        df = transform_source(source)
        assert df is not None
        assert any("score_gauche" in c for c in df.columns)
        assert any("score_extreme_droite" in c for c in df.columns)
        assert any("axe_gd" in c for c in df.columns)

    def test_qpv_has_flag(self):
        from pipeline.transform import transform_source
        source = get_source_by_id("qpv")
        if not source:
            pytest.skip()
        df = transform_source(source)
        assert df is not None
        assert "flag_qpv" in df.columns
        assert "nb_qpv" in df.columns
        assert df["flag_qpv"].isin([0, 1]).all()

    def test_zrr_has_flag(self):
        from pipeline.transform import transform_source
        source = get_source_by_id("zrr")
        if not source:
            pytest.skip()
        df = transform_source(source)
        assert df is not None
        assert "flag_zrr" in df.columns
        assert df["flag_zrr"].isin([0, 1]).all()

    def test_ips_ecoles_has_mean(self):
        from pipeline.transform import transform_source
        source = get_source_by_id("ips_ecoles")
        if not source:
            pytest.skip()
        df = transform_source(source)
        assert df is not None
        assert "ips_ecoles" in df.columns
        assert df["ips_ecoles"].between(50, 200).all()
