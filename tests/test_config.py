"""Tests pour pipeline/config.py."""

from pathlib import Path

from pipeline.config import (
    ROOT_DIR,
    SOURCES_PATH,
    get_familles_politiques,
    get_source_by_id,
    get_sources,
    load_sources_config,
    raw_path_for_source,
    processed_path_for_source,
)


def test_root_dir_exists():
    assert ROOT_DIR.exists()
    assert (ROOT_DIR / "pipeline").is_dir()
    assert (ROOT_DIR / "db").is_dir()


def test_sources_yaml_exists():
    assert SOURCES_PATH.exists()


def test_load_sources_config_returns_dict():
    config = load_sources_config()
    assert isinstance(config, dict)
    assert "sources" in config
    assert "familles_politiques" in config


def test_get_sources_returns_list():
    sources = get_sources()
    assert isinstance(sources, list)
    assert len(sources) > 20  # On a ~34 sources


def test_each_source_has_required_fields():
    for source in get_sources():
        assert "id" in source, f"Source sans id : {source}"
        assert "name" in source, f"Source {source['id']} sans name"
        assert "category" in source, f"Source {source['id']} sans category"
        assert "download" in source, f"Source {source['id']} sans download"


def test_source_ids_are_unique():
    sources = get_sources()
    ids = [s["id"] for s in sources]
    assert len(ids) == len(set(ids)), f"IDs dupliqués : {[x for x in ids if ids.count(x) > 1]}"


def test_get_source_by_id_found():
    source = get_source_by_id("loyers_2025")
    assert source is not None
    assert source["id"] == "loyers_2025"
    assert source["category"] == "logement"


def test_get_source_by_id_not_found():
    assert get_source_by_id("inexistant_xyz") is None


def test_familles_politiques():
    familles = get_familles_politiques()
    assert "gauche" in familles
    assert "droite" in familles
    assert "extreme_droite" in familles
    assert "centre" in familles
    assert isinstance(familles["gauche"], list)
    assert len(familles["gauche"]) > 0


def test_raw_path_for_source():
    source = get_source_by_id("loyers_2025")
    path = raw_path_for_source(source)
    assert isinstance(path, Path)
    assert path.name == "loyers_2025.csv"


def test_processed_path_for_source():
    source = get_source_by_id("loyers_2025")
    path = processed_path_for_source(source)
    assert isinstance(path, Path)
    assert path.suffix == ".parquet"
    assert "loyers_2025" in path.name


def test_download_types_are_valid():
    valid_types = {"direct_url", "insee_zip", "geojson", "custom"}
    for source in get_sources():
        dl_type = source["download"].get("type", "direct_url")
        assert dl_type in valid_types, f"Source {source['id']} a un type inconnu : {dl_type}"


def test_categories_are_valid():
    valid_categories = {
        "revenus", "emploi", "logement", "education", "transport",
        "securite", "sante", "vie_locale", "territoire", "electoral",
    }
    for source in get_sources():
        cat = source.get("category", "")
        assert cat in valid_categories, f"Source {source['id']} a une catégorie inconnue : {cat}"
