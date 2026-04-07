"""Chargement de la configuration et chemins du projet."""

from pathlib import Path

import yaml

# Chemins racine
ROOT_DIR = Path(__file__).resolve().parent.parent
PIPELINE_DIR = ROOT_DIR / "pipeline"
DATA_RAW_DIR = ROOT_DIR / "data" / "raw"
DATA_PROCESSED_DIR = ROOT_DIR / "data" / "processed"
DB_DIR = ROOT_DIR / "db"
DB_PATH = DB_DIR / "votesocio.duckdb"
SCHEMA_PATH = DB_DIR / "schema.sql"
SOURCES_PATH = PIPELINE_DIR / "sources.yaml"


def load_sources_config() -> dict:
    """Charge et retourne la config complète depuis sources.yaml."""
    with open(SOURCES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_sources() -> list[dict]:
    """Retourne la liste des sources."""
    config = load_sources_config()
    return config.get("sources", [])


def get_source_by_id(source_id: str) -> dict | None:
    """Retourne une source par son id."""
    for source in get_sources():
        if source["id"] == source_id:
            return source
    return None


def get_familles_politiques() -> dict[str, list[str]]:
    """Retourne le mapping nuance → famille politique."""
    config = load_sources_config()
    return config.get("familles_politiques", {})


def raw_path_for_source(source: dict) -> Path:
    """Retourne le chemin du fichier brut pour une source."""
    download = source.get("download", {})
    fmt = download.get("format", "csv")
    filename = download.get("filename", f"{source['id']}.{fmt}")
    return DATA_RAW_DIR / filename


def processed_path_for_source(source: dict) -> Path:
    """Retourne le chemin du fichier transformé pour une source."""
    return DATA_PROCESSED_DIR / f"{source['id']}.parquet"
