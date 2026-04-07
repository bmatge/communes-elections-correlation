"""Étape 3 — Chargement dans DuckDB.

Pour chaque source transformée :
1. Enregistre les métadonnées dans variables_meta
2. Insère les valeurs dans commune_data / commune_data_cat
3. Régénère la vue communes_wide
"""

import logging

import duckdb
import pandas as pd

from pipeline.config import (
    DATA_PROCESSED_DIR,
    DATA_RAW_DIR,
    DB_PATH,
    SCHEMA_PATH,
    get_sources,
    processed_path_for_source,
)

logger = logging.getLogger(__name__)


def init_db(con: duckdb.DuckDBPyConnection) -> None:
    """Crée les tables si elles n'existent pas."""
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    con.execute(schema_sql)
    logger.info("Schéma initialisé")


def _compute_superficie(communes: pd.DataFrame, geo_path) -> pd.DataFrame:
    """Calcule la superficie (km²) et la densité depuis les contours GeoJSON.

    Projette les géométries en Lambert-93 (EPSG:2154) pour un calcul d'aire précis.
    """
    import json

    from pyproj import Transformer
    from shapely.geometry import shape
    from shapely.ops import transform

    geo = pd.read_parquet(geo_path, columns=["code_commune", "geometry"])
    proj = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)

    superficies = {}
    for _, row in geo.iterrows():
        try:
            geom = shape(json.loads(row["geometry"]))
            geom_proj = transform(proj.transform, geom)
            superficies[row["code_commune"]] = round(geom_proj.area / 1e6, 2)
        except Exception:
            pass

    sup_df = pd.DataFrame(
        list(superficies.items()), columns=["code_commune", "superficie"]
    )
    communes = communes.merge(sup_df, on="code_commune", how="left")
    communes["densite"] = (
        communes["population"] / communes["superficie"]
    ).round(1)

    logger.info(
        "Superficie calculée pour %d communes (%.0f%% couverture)",
        sup_df.shape[0],
        100 * sup_df.shape[0] / len(communes),
    )
    return communes


def populate_communes(con: duckdb.DuckDBPyConnection) -> int:
    """Peuple la table communes depuis les données disponibles.

    Croise grille_densite (référentiel communes), rp_population (population),
    et epci_communes (intercommunalité).
    """
    # 1. Référentiel de base : grille_densite.csv (code, libellé, région)
    grille_path = DATA_RAW_DIR / "grille_densite.csv"
    if not grille_path.exists():
        logger.warning("grille_densite.csv introuvable, table communes non peuplée")
        return 0

    grille = pd.read_csv(grille_path, sep=";", encoding="utf-8")
    grille.columns = [c.replace("\n", " ").strip() for c in grille.columns]
    cols = list(grille.columns)
    grille = grille.rename(columns={cols[0]: "code_commune", cols[1]: "libelle", cols[3]: "code_region"})
    grille["code_commune"] = grille["code_commune"].astype(str).str.zfill(5)
    grille["code_region"] = grille["code_region"].astype(str)

    # Code département depuis code_commune (2 premiers chars, sauf Corse 2A/2B)
    grille["code_departement"] = grille["code_commune"].str[:2]
    # Corrections DOM : code_commune 97X → département 97X
    mask_dom = grille["code_commune"].str.startswith("97")
    grille.loc[mask_dom, "code_departement"] = grille.loc[mask_dom, "code_commune"].str[:3]

    communes = grille[["code_commune", "libelle", "code_departement", "code_region"]].copy()

    # 2. Population depuis rp_population_2022
    pop_path = DATA_PROCESSED_DIR / "rp_population_2022.parquet"
    if pop_path.exists():
        pop = pd.read_parquet(pop_path, columns=["code_commune", "population"])
        communes = communes.merge(pop, on="code_commune", how="left")
    else:
        communes["population"] = None

    # 3. EPCI depuis epci_communes
    epci_path = DATA_PROCESSED_DIR / "epci_communes.parquet"
    if epci_path.exists():
        epci = pd.read_parquet(epci_path)
        # insee = code_commune, siren = code_epci, raison_sociale = libelle_epci
        epci_map = epci[["insee", "siren", "raison_sociale"]].drop_duplicates(subset="insee")
        epci_map = epci_map.rename(columns={
            "insee": "code_commune",
            "siren": "code_epci",
            "raison_sociale": "libelle_epci",
        })
        epci_map["code_epci"] = epci_map["code_epci"].astype(str)
        communes = communes.merge(epci_map, on="code_commune", how="left")
    else:
        communes["code_epci"] = None
        communes["libelle_epci"] = None

    # Superficie depuis les contours GeoJSON (geo_communes_50m)
    geo_path = DATA_PROCESSED_DIR / "geo_communes_50m.parquet"
    if geo_path.exists():
        communes = _compute_superficie(communes, geo_path)
    else:
        logger.warning("geo_communes_50m.parquet introuvable, superficie/densité non calculées")
        communes["superficie"] = None
        communes["densite"] = None

    # Réordonner les colonnes pour correspondre au schéma SQL
    communes = communes[[
        "code_commune", "libelle", "code_departement", "code_region",
        "population", "superficie", "densite", "code_epci", "libelle_epci",
    ]]

    # 4. INSERT dans DuckDB (idempotent : DELETE + INSERT)
    con.execute("DELETE FROM communes")
    con.register("communes_df", communes)
    con.execute("INSERT INTO communes SELECT * FROM communes_df")
    con.unregister("communes_df")

    n = len(communes)
    logger.info("Table communes peuplée : %d communes", n)
    return n


def load_variables_meta(con: duckdb.DuckDBPyConnection, source: dict) -> None:
    """Insère les métadonnées des variables d'une source.

    Enregistre les variables déclarées dans le YAML ET les variables
    auto-détectées depuis le DataFrame transformé (produites par les transformers).
    """
    source_id = source["id"]
    year = source.get("year")
    category = source.get("category", "")

    all_vars = []
    declared_ids = set()

    # Variables directes (déclarées dans YAML)
    for var in source.get("variables", []):
        declared_ids.add(var["id"])
        all_vars.append({
            "variable_id": var["id"],
            "source_id": source_id,
            "name": var.get("name", var["id"]),
            "description": var.get("description", ""),
            "category": var.get("category", category),
            "type": var.get("type", "numeric"),
            "unit": var.get("unit", ""),
            "year": year,
        })

    # Variables calculées (déclarées dans YAML)
    for comp in source.get("computed", []):
        declared_ids.add(comp["id"])
        all_vars.append({
            "variable_id": comp["id"],
            "source_id": source_id,
            "name": comp.get("name", comp["id"]),
            "description": comp.get("description", ""),
            "category": comp.get("category", category),
            "type": comp.get("type", "numeric"),
            "unit": comp.get("unit", ""),
            "year": year,
        })

    # Variables auto-détectées depuis le DataFrame transformé
    path = processed_path_for_source(source)
    if path.exists():
        import pandas as pd
        df = pd.read_parquet(path)
        meta_cols = {"code_commune", "id_election", "nuance", "famille", "libelle_liste"}
        for col in df.columns:
            if col not in meta_cols and col not in declared_ids:
                var_type = "categorical" if df[col].dtype in ("object", "category") else "numeric"
                all_vars.append({
                    "variable_id": col,
                    "source_id": source_id,
                    "name": col.replace("_", " ").title(),
                    "description": f"Auto-détecté depuis {source_id}",
                    "category": category,
                    "type": var_type,
                    "unit": "",
                    "year": year,
                })

    if not all_vars:
        return

    # DELETE + INSERT (idempotent)
    con.execute("DELETE FROM variables_meta WHERE source_id = ?", [source_id])

    for var in all_vars:
        con.execute(
            """INSERT INTO variables_meta
               (variable_id, source_id, name, description, category, type, unit, year)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                var["variable_id"], var["source_id"], var["name"],
                var["description"], var["category"], var["type"],
                var["unit"], var["year"],
            ],
        )

    logger.info("[%s] %d variables enregistrées dans variables_meta", source_id, len(all_vars))


def load_commune_data(con: duckdb.DuckDBPyConnection, source: dict) -> int:
    """Charge les données transformées dans commune_data / commune_data_cat."""
    source_id = source["id"]
    path = processed_path_for_source(source)

    if not path.exists():
        logger.warning("[%s] Fichier transformé introuvable : %s", source_id, path)
        return 0

    df = pd.read_parquet(path)

    if "code_commune" not in df.columns:
        logger.warning("[%s] Colonne 'code_commune' absente", source_id)
        return 0

    # Identifier les colonnes de variables (tout sauf code_commune et métadonnées)
    meta_cols = {"code_commune", "id_election", "nuance", "famille", "libelle_liste"}
    var_cols = [c for c in df.columns if c not in meta_cols]

    # Séparer numériques et catégorielles
    # D'abord depuis la config YAML
    declared_vars = {v["id"]: v for v in source.get("variables", [])}
    declared_vars.update({v["id"]: v for v in source.get("computed", [])})

    # Ensuite, auto-détecter les colonnes du DataFrame non déclarées dans le YAML
    # (produites par les transformers custom)
    all_vars = dict(declared_vars)
    for col in var_cols:
        if col not in all_vars:
            # Auto-détection du type depuis le dtype pandas
            if df[col].dtype in ("object", "category"):
                all_vars[col] = {"id": col, "type": "categorical"}
            else:
                all_vars[col] = {"id": col, "type": "numeric"}

    numeric_vars = []
    cat_vars = []
    for col in var_cols:
        var_def = all_vars.get(col, {})
        var_type = var_def.get("type", "numeric")
        if var_type == "categorical":
            cat_vars.append(col)
        else:
            numeric_vars.append(col)

    rows_inserted = 0

    # DELETE existing data for this source (toutes les variables, déclarées ou auto-détectées)
    all_var_ids = [v for v in var_cols if v in all_vars]
    if all_var_ids:
        placeholders = ",".join(["?"] * len(all_var_ids))
        con.execute(f"DELETE FROM commune_data WHERE variable_id IN ({placeholders})", all_var_ids)
        con.execute(f"DELETE FROM commune_data_cat WHERE variable_id IN ({placeholders})", all_var_ids)

    # INSERT numériques (melt → long format)
    if numeric_vars:
        present_numeric = [c for c in numeric_vars if c in df.columns]
        if present_numeric:
            melted = df[["code_commune"] + present_numeric].melt(
                id_vars="code_commune",
                var_name="variable_id",
                value_name="value",
            )
            melted = melted.dropna(subset=["value"])
            melted["code_commune"] = melted["code_commune"].astype(str)

            con.execute("INSERT INTO commune_data SELECT * FROM melted")
            rows_inserted += len(melted)

    # INSERT catégorielles
    if cat_vars:
        present_cat = [c for c in cat_vars if c in df.columns]
        if present_cat:
            melted_cat = df[["code_commune"] + present_cat].melt(
                id_vars="code_commune",
                var_name="variable_id",
                value_name="value",
            )
            melted_cat = melted_cat.dropna(subset=["value"])
            melted_cat["code_commune"] = melted_cat["code_commune"].astype(str)
            melted_cat["value"] = melted_cat["value"].astype(str)

            con.execute("INSERT INTO commune_data_cat SELECT * FROM melted_cat")
            rows_inserted += len(melted_cat)

    logger.info("[%s] %d valeurs insérées", source_id, rows_inserted)
    return rows_inserted


def rebuild_wide_view(con: duckdb.DuckDBPyConnection) -> None:
    """Régénère la vue communes_wide à partir de variables_meta + commune_data."""
    # Récupérer toutes les variables numériques
    vars_df = con.execute(
        "SELECT variable_id FROM variables_meta WHERE type = 'numeric' ORDER BY category, variable_id"
    ).fetchdf()

    if vars_df.empty:
        logger.warning("Aucune variable dans variables_meta, vue wide non créée")
        return

    # Construire les colonnes CASE WHEN
    case_clauses = []
    for var_id in vars_df["variable_id"]:
        safe_name = var_id.replace("-", "_").replace(" ", "_")
        case_clauses.append(
            f"MAX(CASE WHEN cd.variable_id = '{var_id}' THEN cd.value END) AS {safe_name}"
        )

    # Ajouter les catégorielles
    cat_vars_df = con.execute(
        "SELECT variable_id FROM variables_meta WHERE type = 'categorical' ORDER BY variable_id"
    ).fetchdf()

    cat_case_clauses = []
    for var_id in cat_vars_df["variable_id"]:
        safe_name = var_id.replace("-", "_").replace(" ", "_")
        cat_case_clauses.append(
            f"MAX(CASE WHEN cc.variable_id = '{var_id}' THEN cc.value END) AS {safe_name}"
        )

    # Assembler la vue
    all_clauses = ",\n    ".join(case_clauses + cat_case_clauses)

    joins = "LEFT JOIN commune_data cd ON c.code_commune = cd.code_commune"
    if cat_case_clauses:
        joins += "\nLEFT JOIN commune_data_cat cc ON c.code_commune = cc.code_commune"

    sql = f"""CREATE OR REPLACE VIEW communes_wide AS
SELECT
    c.*,
    {all_clauses}
FROM communes c
{joins}
GROUP BY ALL"""

    con.execute(sql)

    # Compter les colonnes
    ncols = len(case_clauses) + len(cat_case_clauses)
    logger.info("Vue communes_wide recréée avec %d variables", ncols)


def load_geo_table(con: duckdb.DuckDBPyConnection, source: dict) -> int:
    """Charge une source géographique directement dans sa table cible.

    Les sources avec target_table (geo_communes, geo_departements, etc.)
    ne passent pas par le modèle EAV. Le DataFrame transformé est inséré
    tel quel dans la table DuckDB correspondante.
    """
    source_id = source["id"]
    target_table = source["target_table"]
    path = processed_path_for_source(source)

    if not path.exists():
        logger.warning("[%s] Fichier transformé introuvable : %s", source_id, path)
        return 0

    df = pd.read_parquet(path)
    logger.info("[%s] Chargement géo → %s (%d lignes)", source_id, target_table, len(df))

    # DELETE + INSERT (idempotent)
    con.execute(f"DELETE FROM {target_table}")
    con.register("geo_df", df)
    con.execute(f"INSERT INTO {target_table} SELECT * FROM geo_df")
    con.unregister("geo_df")

    logger.info("[%s] %d géométries chargées dans %s", source_id, len(df), target_table)
    return len(df)


def load_source(con: duckdb.DuckDBPyConnection, source: dict) -> int:
    """Charge une source complète dans DuckDB."""
    # Sources géographiques → table dédiée (pas EAV)
    if "target_table" in source:
        return load_geo_table(con, source)

    load_variables_meta(con, source)
    rows = load_commune_data(con, source)
    return rows


def load_all(source_ids: list[str] | None = None) -> None:
    """Charge toutes les sources dans DuckDB et reconstruit la vue wide."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))

    try:
        init_db(con)
        populate_communes(con)

        sources = get_sources()
        if source_ids:
            sources = [s for s in sources if s["id"] in source_ids]

        total_rows = 0
        for source in sources:
            try:
                rows = load_source(con, source)
                total_rows += rows
            except Exception:
                logger.exception("[%s] ERREUR de chargement", source["id"])

        rebuild_wide_view(con)
        logger.info("Chargement terminé : %d valeurs insérées au total", total_rows)

    finally:
        con.close()


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Chargement DuckDB VoteSocio")
    parser.add_argument("--source", "-s", nargs="*", help="IDs des sources à charger")
    args = parser.parse_args()

    load_all(source_ids=args.source)
