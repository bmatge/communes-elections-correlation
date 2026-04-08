"""Tests pour pipeline/load.py."""

import tempfile
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from pipeline.config import SCHEMA_PATH


@pytest.fixture
def tmp_db():
    """Crée une BDD DuckDB temporaire avec le schéma."""
    tmp_dir = tempfile.mkdtemp()
    db_path = Path(tmp_dir) / "test.duckdb"

    con = duckdb.connect(str(db_path))
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    con.execute(schema_sql)
    yield con
    con.close()
    db_path.unlink(missing_ok=True)
    Path(tmp_dir).rmdir()


def test_schema_creates_tables(tmp_db):
    tables = tmp_db.execute("SHOW TABLES").fetchdf()["name"].tolist()
    assert "communes" in tables
    assert "variables_meta" in tables
    assert "commune_data" in tables
    assert "commune_data_cat" in tables
    assert "elections_raw" in tables
    assert "geo_communes" in tables
    assert "regression_coefficients" in tables
    assert "anomalies" in tables


def test_insert_and_query_commune_data(tmp_db):
    # Insérer des données test
    tmp_db.execute("INSERT INTO variables_meta (variable_id, source_id, name, description, category, type, unit, year) VALUES ('test_var', 'test_src', 'Test', '', 'test', 'numeric', '', 2021)")
    tmp_db.execute("INSERT INTO commune_data VALUES ('01001', 'test_var', 42.0)")
    tmp_db.execute("INSERT INTO commune_data VALUES ('75056', 'test_var', 99.0)")

    result = tmp_db.execute("SELECT * FROM commune_data WHERE variable_id = 'test_var' ORDER BY code_commune").fetchdf()
    assert len(result) == 2
    assert result.iloc[0]["value"] == 42.0
    assert result.iloc[1]["code_commune"] == "75056"


def test_primary_key_prevents_duplicates(tmp_db):
    tmp_db.execute("INSERT INTO commune_data VALUES ('01001', 'var1', 10.0)")
    with pytest.raises(duckdb.ConstraintException):
        tmp_db.execute("INSERT INTO commune_data VALUES ('01001', 'var1', 20.0)")


def test_variables_meta_categories(tmp_db):
    tmp_db.execute("INSERT INTO variables_meta (variable_id, source_id, name, description, category, type, unit, year) VALUES ('v1', 's1', 'V1', '', 'revenus', 'numeric', '€', 2021)")
    tmp_db.execute("INSERT INTO variables_meta (variable_id, source_id, name, description, category, type, unit, year) VALUES ('v2', 's1', 'V2', '', 'emploi', 'numeric', '%', 2021)")
    tmp_db.execute("INSERT INTO variables_meta (variable_id, source_id, name, description, category, type, unit, year) VALUES ('v3', 's2', 'V3', '', 'revenus', 'numeric', '€', 2021)")

    result = tmp_db.execute("SELECT category, COUNT(*) AS n FROM variables_meta GROUP BY category ORDER BY category").fetchdf()
    assert len(result) == 2
    assert result.iloc[0]["category"] == "emploi"
    assert result.iloc[1]["n"] == 2  # 2 variables revenus


class TestWithRealDB:
    """Tests sur la BDD réelle (si elle existe)."""

    @pytest.fixture(autouse=True)
    def check_db(self):
        from pipeline.config import DB_PATH
        if not DB_PATH.exists():
            pytest.skip("BDD votesocio.duckdb non trouvée")

    def test_real_db_has_data(self):
        from pipeline.config import DB_PATH
        con = duckdb.connect(str(DB_PATH), read_only=True)
        count = con.execute("SELECT COUNT(*) FROM commune_data").fetchone()[0]
        con.close()
        assert count > 100000

    def test_real_db_has_variables_meta(self):
        from pipeline.config import DB_PATH
        con = duckdb.connect(str(DB_PATH), read_only=True)
        count = con.execute("SELECT COUNT(*) FROM variables_meta").fetchone()[0]
        con.close()
        assert count > 50

    def test_real_db_electoral_variables(self):
        from pipeline.config import DB_PATH
        con = duckdb.connect(str(DB_PATH), read_only=True)
        electoral = con.execute(
            "SELECT COUNT(*) FROM variables_meta WHERE category = 'electoral'"
        ).fetchone()[0]
        con.close()
        assert electoral > 30
