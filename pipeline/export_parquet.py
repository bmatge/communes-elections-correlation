"""Export des tables DuckDB en fichiers Parquet pour le front-end (DuckDB-WASM).

Usage:
    python -m pipeline.export_parquet [--output web/static/data]
"""
import argparse
import sys
from pathlib import Path

import duckdb

from pipeline.config import DB_PATH, ROOT_DIR

TABLES = [
    "commune_data",
    "variables_meta",
    "communes",
    "elections_raw",
    "geo_communes",
    "geo_communes_lowres",
    "geo_departements",
    "geo_regions",
    # Tables d'analyse
    "correlation_matrix",
    "commune_zscores",
    "regression_results",
    "commune_residuals",
    "commune_clusters",
    "cluster_profiles",
    "pca_loadings",
    "regression_scaler",
    "decalage_local_national",
]

DEFAULT_OUTPUT = ROOT_DIR / "web" / "static" / "data"


def export_parquet(output_dir: Path | None = None) -> None:
    output = output_dir or DEFAULT_OUTPUT
    output.mkdir(parents=True, exist_ok=True)

    if not DB_PATH.exists():
        print(f"Erreur : base DuckDB introuvable ({DB_PATH})")
        sys.exit(1)

    con = duckdb.connect(str(DB_PATH), read_only=True)

    for table in TABLES:
        dest = output / f"{table}.parquet"
        try:
            count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if count == 0:
                print(f"  {table}: vide, ignoré")
                continue
            con.execute(f"COPY {table} TO '{dest}' (FORMAT PARQUET, COMPRESSION ZSTD)")
            size_kb = dest.stat().st_size / 1024
            print(f"  {table}: {count:,} lignes → {dest.name} ({size_kb:.0f} Ko)")
        except duckdb.CatalogException:
            print(f"  {table}: table absente, ignoré")

    con.close()
    print(f"\nExport terminé → {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Exporter DuckDB → Parquet pour le front")
    parser.add_argument("--output", type=Path, default=None, help="Répertoire de sortie")
    args = parser.parse_args()
    export_parquet(args.output)
