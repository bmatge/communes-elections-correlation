"""B2 — Z-scores départementaux et régionaux.

Pour chaque variable, calcule l'écart de chaque commune à la moyenne de son
département (pondérée par population). Détecte les communes qui dévient de
leur contexte local.

Résultat stocké dans DuckDB : table `commune_zscores`.
"""

import logging

import duckdb
import numpy as np
import pandas as pd

from pipeline.config import DB_PATH

logger = logging.getLogger(__name__)

# Variables clés pour le z-score (sous-ensemble pertinent)
ZSCORE_VARS = [
    # Électorales
    "score_gauche_pres22t1",
    "score_droite_pres22t1",
    "score_extreme_droite_pres22t1",
    "score_centre_pres22t1",
    "pct_abstention_pres22t1",
    "score_gauche_euro24t1",
    "score_droite_euro24t1",
    "score_extreme_droite_euro24t1",
    "score_centre_euro24t1",
    "pct_abstention_euro24t1",
    "score_gauche_legi24t1",
    "score_extreme_droite_legi24t1",
    # Socio-éco
    "revenu_median",
    "taux_pauvrete",
    "pct_diplomes_sup",
    "pct_sans_diplome",
    "pct_cadres",
    "pct_ouvriers",
    "pct_hlm",
    "pct_proprietaires",
    "taux_chomage",
    "pct_etrangers",
    "pct_immigres",
    "pct_60plus",
    "pct_jeunes",
]


def compute_zscores(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Calcule les z-scores départementaux pondérés par population."""
    # Charger communes + données
    communes = con.execute(
        "SELECT code_commune, code_departement, population FROM communes"
    ).fetchdf()

    # Vérifier quelles variables existent
    existing = con.execute(
        "SELECT DISTINCT variable_id FROM commune_data"
    ).fetchdf()["variable_id"].tolist()
    vars_to_compute = [v for v in ZSCORE_VARS if v in existing]

    logger.info("Z-scores pour %d variables", len(vars_to_compute))

    placeholders = ",".join(["?"] * len(vars_to_compute))
    data = con.execute(
        f"""
        SELECT code_commune, variable_id, value
        FROM commune_data
        WHERE variable_id IN ({placeholders})
        """,
        vars_to_compute,
    ).fetchdf()

    # Pivot
    wide = data.pivot(index="code_commune", columns="variable_id", values="value")
    wide = wide.merge(communes, on="code_commune", how="inner")

    results = []
    for var in vars_to_compute:
        if var not in wide.columns:
            continue
        sub = wide[["code_commune", "code_departement", "population", var]].dropna()
        if sub.empty:
            continue

        # Moyenne et écart-type départementaux (pondérés par population)
        dept_stats = sub.groupby("code_departement").apply(
            lambda g: pd.Series({
                "dept_mean": np.average(g[var], weights=g["population"].fillna(1)),
                "dept_std": _weighted_std(g[var], g["population"].fillna(1)),
                "dept_n": len(g),
            }),
            include_groups=False,
        )
        dept_stats = dept_stats[dept_stats["dept_std"] > 0]

        sub = sub.merge(dept_stats, left_on="code_departement", right_index=True)
        sub["zscore"] = (sub[var] - sub["dept_mean"]) / sub["dept_std"]
        sub["variable_id"] = var

        results.append(
            sub[["code_commune", "variable_id", "zscore", "dept_mean", "dept_std"]].copy()
        )

    if not results:
        return pd.DataFrame()

    return pd.concat(results, ignore_index=True)


def _weighted_std(values, weights):
    """Écart-type pondéré."""
    w = weights.values
    v = values.values
    avg = np.average(v, weights=w)
    variance = np.average((v - avg) ** 2, weights=w)
    return np.sqrt(variance)


def find_anomalies(zscores_df: pd.DataFrame, threshold: float = 2.5) -> pd.DataFrame:
    """Identifie les communes avec z-score > seuil (en valeur absolue)."""
    anomalies = zscores_df[zscores_df["zscore"].abs() >= threshold].copy()
    anomalies = anomalies.sort_values("zscore", key=abs, ascending=False)
    return anomalies


def save_to_db(zscores_df: pd.DataFrame, con: duckdb.DuckDBPyConnection) -> None:
    """Sauvegarde les z-scores dans DuckDB."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS commune_zscores (
            code_commune VARCHAR,
            variable_id VARCHAR,
            zscore DOUBLE,
            dept_mean DOUBLE,
            dept_std DOUBLE,
            PRIMARY KEY (code_commune, variable_id)
        )
    """)
    con.execute("DELETE FROM commune_zscores")
    con.register("zscores_df", zscores_df)
    con.execute("INSERT INTO commune_zscores SELECT * FROM zscores_df")
    con.unregister("zscores_df")
    logger.info("%d z-scores sauvegardés", len(zscores_df))


def run() -> pd.DataFrame:
    """Point d'entrée principal."""
    con = duckdb.connect(str(DB_PATH))
    try:
        zscores = compute_zscores(con)
        if zscores.empty:
            logger.warning("Aucun z-score calculé")
            return pd.DataFrame()

        save_to_db(zscores, con)

        # Trouver les anomalies
        anomalies = find_anomalies(zscores, threshold=3.0)

        # Joindre les noms des communes
        communes = con.execute(
            "SELECT code_commune, libelle, code_departement, population FROM communes"
        ).fetchdf()
        anomalies = anomalies.merge(communes, on="code_commune", how="left")

        # Afficher les plus extrêmes
        print("\n" + "=" * 90)
        print("COMMUNES LES PLUS ATYPIQUES (|z-score| ≥ 3.0)")
        print("=" * 90)

        # Grouper par type de variable
        for var in ZSCORE_VARS[:12]:  # Électorales seulement pour l'affichage
            sub = anomalies[anomalies["variable_id"] == var].head(10)
            if sub.empty:
                continue
            print(f"\n  {var}:")
            for _, row in sub.iterrows():
                sign = "+" if row["zscore"] > 0 else ""
                print(
                    f"    {sign}{row['zscore']:+.1f}σ  {row['libelle']:30s} "
                    f"({row['code_departement']}, pop={row['population']:.0f})"
                )

        # Stats globales
        print(f"\nTotal : {len(anomalies)} anomalies (|z| ≥ 3.0) sur {len(zscores)} z-scores")

        return zscores
    finally:
        con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
