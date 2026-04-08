"""B1 — Matrice de corrélation socio-éco × scores électoraux.

Calcule les corrélations de Pearson et Spearman entre toutes les variables
socio-économiques et les scores électoraux, puis stocke les résultats
dans DuckDB (table `correlation_matrix`).
"""

import logging

import duckdb
import pandas as pd

from pipeline.config import DB_PATH

logger = logging.getLogger(__name__)

# Scrutins de référence (les plus récents / pertinents)
SCRUTINS_CLES = [
    "pres22t1",
    "legi24t1",
    "euro24t1",
    "muni26t1",
]

# Variables électorales d'intérêt (familles + abstention)
FAMILLES = ["gauche", "droite", "extreme_droite", "centre"]
ELECTORAL_SUFFIXES = (
    [f"score_{f}_{s}" for f in FAMILLES for s in SCRUTINS_CLES]
    + [f"pct_abstention_{s}" for s in SCRUTINS_CLES]
)


def build_wide_dataframe(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Construit le DataFrame large communes × variables depuis DuckDB."""
    # Récupérer toutes les variables numériques
    vars_df = con.execute(
        "SELECT variable_id, category FROM variables_meta WHERE type = 'numeric'"
    ).fetchdf()

    socio_vars = vars_df[vars_df["category"] != "electoral"]["variable_id"].tolist()
    elec_vars = [v for v in ELECTORAL_SUFFIXES if v in vars_df["variable_id"].values]

    all_vars = socio_vars + elec_vars
    if not all_vars:
        logger.warning("Aucune variable trouvée")
        return pd.DataFrame()

    placeholders = ",".join(["?"] * len(all_vars))

    # Pivot depuis commune_data
    df = con.execute(
        f"""
        SELECT code_commune, variable_id, value
        FROM commune_data
        WHERE variable_id IN ({placeholders})
        """,
        all_vars,
    ).fetchdf()

    wide = df.pivot(index="code_commune", columns="variable_id", values="value")
    wide = wide.reset_index()

    # Joindre les infos communes (population, département)
    communes = con.execute(
        "SELECT code_commune, libelle, code_departement, code_region, population, densite FROM communes"
    ).fetchdf()
    wide = wide.merge(communes, on="code_commune", how="inner")

    logger.info(
        "DataFrame wide : %d communes × %d variables (%d socio-éco, %d électorales)",
        len(wide), len(socio_vars) + len(elec_vars), len(socio_vars), len(elec_vars),
    )

    return wide


def compute_correlation_matrix(
    wide: pd.DataFrame,
    method: str = "pearson",
    min_obs: int = 1000,
) -> pd.DataFrame:
    """Calcule la matrice de corrélation socio-éco × électorales.

    Returns
    -------
    DataFrame avec colonnes: socio_var, electoral_var, correlation, p_value, n_obs
    """
    from scipy import stats

    socio_cols = [c for c in wide.columns if c not in _meta_cols() and not _is_electoral(c)]
    elec_cols = [c for c in wide.columns if _is_electoral(c)]

    results = []
    for s in socio_cols:
        for e in elec_cols:
            pair = wide[[s, e]].dropna()
            n = len(pair)
            if n < min_obs:
                continue
            if method == "pearson":
                corr, pval = stats.pearsonr(pair[s], pair[e])
            else:
                corr, pval = stats.spearmanr(pair[s], pair[e])
            results.append({
                "socio_var": s,
                "electoral_var": e,
                "correlation": round(corr, 4),
                "p_value": pval,
                "n_obs": n,
                "method": method,
            })

    return pd.DataFrame(results)


def top_correlations(corr_df: pd.DataFrame, n: int = 30) -> pd.DataFrame:
    """Retourne les N corrélations les plus fortes (en valeur absolue)."""
    corr_df["abs_corr"] = corr_df["correlation"].abs()
    top = corr_df.nlargest(n, "abs_corr").drop(columns=["abs_corr"])
    return top


def save_to_db(corr_df: pd.DataFrame, con: duckdb.DuckDBPyConnection) -> None:
    """Sauvegarde la matrice de corrélation dans DuckDB."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS correlation_matrix (
            socio_var VARCHAR,
            electoral_var VARCHAR,
            correlation DOUBLE,
            p_value DOUBLE,
            n_obs INTEGER,
            method VARCHAR,
            PRIMARY KEY (socio_var, electoral_var, method)
        )
    """)
    con.execute("DELETE FROM correlation_matrix")
    con.register("corr_df", corr_df)
    con.execute("INSERT INTO correlation_matrix SELECT * FROM corr_df")
    con.unregister("corr_df")
    logger.info("%d corrélations sauvegardées dans correlation_matrix", len(corr_df))


def _meta_cols():
    return {"code_commune", "libelle", "code_departement", "code_region", "population", "densite"}


def _is_electoral(col: str) -> bool:
    return col.startswith("score_") or col.startswith("pct_abstention") or col.startswith("pct_participation")


def run() -> pd.DataFrame:
    """Point d'entrée principal."""
    con = duckdb.connect(str(DB_PATH))
    try:
        wide = build_wide_dataframe(con)
        if wide.empty:
            return pd.DataFrame()

        # Pearson
        corr_pearson = compute_correlation_matrix(wide, method="pearson")
        # Spearman
        corr_spearman = compute_correlation_matrix(wide, method="spearman")

        corr_all = pd.concat([corr_pearson, corr_spearman], ignore_index=True)
        save_to_db(corr_all, con)

        # Afficher le top
        top = top_correlations(corr_pearson, n=30)
        print("\n" + "=" * 80)
        print("TOP 30 CORRÉLATIONS (Pearson) — socio-éco × électorales")
        print("=" * 80)
        for _, row in top.iterrows():
            sign = "+" if row["correlation"] > 0 else ""
            print(f"  {sign}{row['correlation']:.3f}  {row['socio_var']:30s} × {row['electoral_var']}")
        print()

        return corr_all
    finally:
        con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
