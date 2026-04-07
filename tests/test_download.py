"""Tests pour pipeline/download.py."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pipeline.download import download_file, download_source


def test_download_source_skips_existing(tmp_path):
    """Ne re-télécharge pas si le fichier existe déjà."""
    source = {
        "id": "test_source",
        "download": {"type": "direct_url", "url": "https://example.com/test.csv", "format": "csv"},
    }
    # Créer un fichier factice
    dest = tmp_path / "test_source.csv"
    dest.write_text("fake data")

    with patch("pipeline.download.raw_path_for_source", return_value=dest):
        result = download_source(source, force=False)
        assert result == dest  # Retourne le chemin existant sans télécharger


def test_download_source_custom_returns_none():
    """Les sources custom retournent None."""
    source = {
        "id": "test_custom",
        "download": {"type": "custom", "url": "https://example.com"},
    }
    with patch("pipeline.download.raw_path_for_source", return_value=Path("/tmp/test.csv")):
        result = download_source(source, force=False)
        assert result is None


def test_download_source_unknown_type():
    """Les types inconnus retournent None."""
    source = {
        "id": "test_unknown",
        "download": {"type": "unknown_type", "url": "https://example.com"},
    }
    fake_path = Path("/tmp/nonexistent_file.csv")
    with patch("pipeline.download.raw_path_for_source", return_value=fake_path):
        result = download_source(source, force=False)
        assert result is None
