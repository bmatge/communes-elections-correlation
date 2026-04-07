"""Étape 2 — Transformation des données brutes.

Pour chaque source :
1. Charge le fichier brut
2. Applique le mapping de colonnes (depuis sources.yaml)
3. Calcule les ratios/formules déclarées
4. Applique un transformer custom si présent dans pipeline/transformers/
5. Écrit le résultat en Parquet dans data/processed/
"""

import importlib
import logging
from pathlib import Path

import pandas as pd

from pipeline.config import (
    DATA_PROCESSED_DIR,
    get_sources,
    raw_path_for_source,
    processed_path_for_source,
)

logger = logging.getLogger(__name__)


def load_raw_file(source: dict) -> pd.DataFrame | None:
    """Charge un fichier brut selon son format."""
    path = raw_path_for_source(source)
    if not path.exists():
        logger.warning("[%s] Fichier brut introuvable : %s", source["id"], path)
        return None

    download_cfg = source.get("download", {})
    fmt = download_cfg.get("format", "csv")
    encoding = download_cfg.get("encoding", "utf-8")
    separator = download_cfg.get("separator", ",")

    logger.info("[%s] Chargement %s : %s", source["id"], fmt, path.name)

    if fmt == "parquet":
        return pd.read_parquet(path)
    elif fmt in ("csv", "csv.gz"):
        decimal = download_cfg.get("decimal", ".")
        try:
            return pd.read_csv(path, encoding=encoding, sep=separator, decimal=decimal, low_memory=False)
        except UnicodeDecodeError:
            logger.warning("[%s] Échec encoding %s, retry en latin-1", source["id"], encoding)
            return pd.read_csv(path, encoding="latin-1", sep=separator, decimal=decimal, low_memory=False)
    elif fmt == "xlsx":
        return pd.read_excel(path, engine="openpyxl")
    elif fmt == "xls":
        return pd.read_excel(path, engine="xlrd")
    elif fmt in ("geojson", "geojson.gz"):
        # GeoJSON : retourne un DataFrame vide, le transformer custom
        # (geo_contours) se charge du parsing
        return pd.DataFrame()
    else:
        logger.warning("[%s] Format non supporté : %s", source["id"], fmt)
        return None


def apply_filter(df: pd.DataFrame, source: dict) -> pd.DataFrame:
    """Applique les filtres déclarés dans la config."""
    filters = source.get("filter", {})
    for col, values in filters.items():
        if col in df.columns:
            before = len(df)
            df = df[df[col].isin(values)]
            logger.info("[%s] Filtre %s IN %s : %d → %d lignes", source["id"], col, values, before, len(df))
    return df


def apply_column_mapping(df: pd.DataFrame, source: dict) -> pd.DataFrame:
    """Extrait et renomme les colonnes déclarées dans variables."""
    variables = source.get("variables", [])
    if not variables:
        return df

    join_key = source.get("join_key", "CODGEO")

    # Construire le mapping source_col → variable_id
    mapping = {}
    for var in variables:
        src_col = var.get("source_col")
        var_id = var["id"]
        if src_col and src_col in df.columns:
            mapping[src_col] = var_id
        elif src_col:
            logger.warning("[%s] Colonne '%s' absente du fichier", source["id"], src_col)

    if not mapping:
        return df

    # Garder la clé de jointure + les colonnes mappées
    cols_to_keep = [join_key] + list(mapping.keys())
    cols_present = [c for c in cols_to_keep if c in df.columns]
    result = df[cols_present].copy()
    result = result.rename(columns=mapping)

    # Renommer la clé de jointure en code_commune
    if join_key != "code_commune" and join_key in result.columns:
        result = result.rename(columns={join_key: "code_commune"})

    return result


def apply_computed_variables(df: pd.DataFrame, source: dict) -> pd.DataFrame:
    """Calcule les variables dérivées (formules du YAML)."""
    computed = source.get("computed", [])
    if not computed:
        return df

    for comp in computed:
        var_id = comp["id"]
        formula = comp["formula"]
        try:
            # Les formules référencent des variable_id déjà présents comme colonnes
            df[var_id] = df.eval(formula)
            logger.info("[%s] Variable calculée : %s = %s", source["id"], var_id, formula)
        except Exception as e:
            logger.warning("[%s] Erreur calcul '%s' = '%s' : %s", source["id"], var_id, formula, e)

    return df


def apply_custom_transformer(df: pd.DataFrame, source: dict) -> pd.DataFrame:
    """Charge et applique un transformer custom si spécifié."""
    transformer_name = source.get("transformer")
    if not transformer_name:
        return df

    try:
        module = importlib.import_module(f"pipeline.transformers.{transformer_name}")
        if hasattr(module, "transform"):
            logger.info("[%s] Transformer custom : %s", source["id"], transformer_name)
            df = module.transform(df, source)
        else:
            logger.warning("[%s] Transformer '%s' n'a pas de fonction transform()", source["id"], transformer_name)
    except ModuleNotFoundError:
        logger.warning("[%s] Transformer '%s' non trouvé (à créer dans pipeline/transformers/)", source["id"], transformer_name)

    return df


def transform_source(source: dict) -> pd.DataFrame | None:
    """Pipeline de transformation complet pour une source."""
    source_id = source["id"]

    # Charger
    df = load_raw_file(source)
    if df is None:
        return None

    logger.info("[%s] %d lignes × %d colonnes chargées", source_id, len(df), len(df.columns))

    # Transformer custom en premier (peut restructurer le DataFrame)
    df = apply_custom_transformer(df, source)

    # Filtrer
    df = apply_filter(df, source)

    # Mapper les colonnes
    df = apply_column_mapping(df, source)

    # Calculer les variables dérivées
    df = apply_computed_variables(df, source)

    # Remapper les arrondissements PLM vers le code commune unique
    # Si la source a un transformer custom, il est responsable du remapping
    # (car il peut nécessiter un traitement spécifique avant agrégation)
    if (
        "code_commune" in df.columns
        and "target_table" not in source
        and not source.get("transformer")
    ):
        from pipeline.transformers import remap_arrondissements

        df = remap_arrondissements(df, col="code_commune")

        if df["code_commune"].duplicated().any():
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            other_cols = [c for c in df.columns if c not in numeric_cols and c != "code_commune"]
            agg_dict = {c: "sum" for c in numeric_cols}
            agg_dict.update({c: "first" for c in other_cols})
            df = df.groupby("code_commune", as_index=False).agg(agg_dict)
            logger.info("[%s] Arrondissements PLM agrégés", source_id)

    logger.info("[%s] Résultat : %d lignes × %d colonnes", source_id, len(df), len(df.columns))

    return df


def transform_and_save(source: dict, force: bool = False) -> Path | None:
    """Transforme une source et sauvegarde en Parquet."""
    dest = processed_path_for_source(source)

    if dest.exists() and not force:
        logger.info("[%s] Déjà transformé : %s", source["id"], dest.name)
        return dest

    df = transform_source(source)
    if df is None or df.empty:
        logger.warning("[%s] Pas de données après transformation", source["id"])
        return None

    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(dest, index=False)
    logger.info("[%s] Sauvegardé → %s", source["id"], dest.name)

    return dest


def transform_all(force: bool = False, source_ids: list[str] | None = None) -> dict[str, Path | None]:
    """Transforme toutes les sources (ou une sélection)."""
    results = {}
    sources = get_sources()

    if source_ids:
        sources = [s for s in sources if s["id"] in source_ids]

    for source in sources:
        source_id = source["id"]
        try:
            path = transform_and_save(source, force=force)
            results[source_id] = path
        except Exception:
            logger.exception("[%s] ERREUR de transformation", source_id)
            results[source_id] = None

    succeeded = sum(1 for v in results.values() if v is not None)
    failed = sum(1 for v in results.values() if v is None)
    logger.info("Transformation terminée : %d OK, %d échoués sur %d", succeeded, failed, len(results))

    return results


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Transformation des données VoteSocio")
    parser.add_argument("--source", "-s", nargs="*", help="IDs des sources à transformer")
    parser.add_argument("--force", "-f", action="store_true", help="Re-transformer même si le fichier existe")
    args = parser.parse_args()

    transform_all(force=args.force, source_ids=args.source)
