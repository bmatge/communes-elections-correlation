"""Transformer geo_contours : parse un GeoJSON de contours administratifs.

Extrait pour chaque feature :
- code (code_commune, code_departement ou code_region selon la source)
- nom
- geometry (string GeoJSON du contour)
- centroid_lat, centroid_lon (calculés depuis la géométrie)

Supporte les fichiers .geojson.gz (décompression automatique).
"""

import gzip
import json
import logging
from pathlib import Path

import pandas as pd

from pipeline.config import raw_path_for_source

logger = logging.getLogger(__name__)

# Mapping target_table → (propriété code, nom colonne code)
TABLE_CODE_MAP = {
    "geo_communes": ("code", "code_commune"),
    "geo_communes_lowres": ("code", "code_commune"),
    "geo_departements": ("code", "code_departement"),
    "geo_regions": ("code", "code_region"),
}


def _centroid(geometry: dict) -> tuple[float, float]:
    """Calcule un centroïde approximatif depuis une géométrie GeoJSON.

    Moyenne des coordonnées (suffisant pour un point de label, pas pour
    de la géodésie). Gère Polygon et MultiPolygon.
    """
    coords = []

    def _extract(obj: list, depth: int = 0) -> None:
        if depth > 5:
            return
        if isinstance(obj[0], (int, float)):
            coords.append(obj)
        else:
            for item in obj:
                _extract(item, depth + 1)

    try:
        _extract(geometry["coordinates"])
    except (KeyError, IndexError, TypeError):
        return 0.0, 0.0

    if not coords:
        return 0.0, 0.0

    lon = sum(c[0] for c in coords) / len(coords)
    lat = sum(c[1] for c in coords) / len(coords)
    return round(lat, 6), round(lon, 6)


def transform(df: pd.DataFrame, source: dict) -> pd.DataFrame:
    """Parse le GeoJSON brut et retourne un DataFrame prêt au chargement.

    Note : le paramètre df est ignoré car le fichier brut est du GeoJSON,
    pas un format tabulaire. On recharge directement depuis le fichier.
    """
    path = raw_path_for_source(source)
    target_table = source.get("target_table", "geo_communes")

    logger.info("[%s] Chargement GeoJSON : %s", source["id"], path.name)

    # Décompresser si gz
    if path.name.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            geojson = json.load(f)
    else:
        with open(path, encoding="utf-8") as f:
            geojson = json.load(f)

    features = geojson.get("features", [])
    logger.info("[%s] %d features extraites", source["id"], len(features))

    # Déterminer la colonne code selon la table cible
    code_prop, code_col = TABLE_CODE_MAP.get(target_table, ("code", "code"))

    rows = []
    for feat in features:
        props = feat.get("properties", {})
        geom = feat.get("geometry")

        code = props.get(code_prop, "")
        nom = props.get("nom", "")

        # Sérialiser la géométrie en string JSON compacte
        geom_str = json.dumps(geom, separators=(",", ":")) if geom else None

        lat, lon = _centroid(geom) if geom else (0.0, 0.0)

        rows.append({
            code_col: str(code),
            "nom": nom,
            "geometry": geom_str,
            "centroid_lat": lat,
            "centroid_lon": lon,
        })

    result = pd.DataFrame(rows)
    logger.info("[%s] → %d lignes, colonnes : %s", source["id"], len(result), list(result.columns))

    return result
