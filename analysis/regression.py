"""B3 — Régression multivariée : prédire les scores électoraux.

Entraîne un modèle OLS pour prédire chaque score électoral à partir du profil
socio-économique. Identifie les variables les plus prédictives et les communes
avec les plus gros résidus (les "anomalies").

Résultats stockés dans DuckDB :
- `regression_results` : coefficients, R², p-values par modèle
- `commune_residuals` : résidus par commune et variable cible
"""

import logging

import duckdb
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from pipeline.config import DB_PATH

logger = logging.getLogger(__name__)

# Variables cibles (scores électoraux clés)
TARGETS = [
    "score_gauche_pres22t1",
    "score_droite_pres22t1",
    "score_extreme_droite_pres22t1",
    "score_centre_pres22t1",
    "pct_abstention_pres22t1",
    "score_gauche_euro24t1",
    "score_extreme_droite_euro24t1",
    "pct_abstention_euro24t1",
    "score_gauche_legi24t1",
    "score_extreme_droite_legi24t1",
]

# Features socio-éco (sélection des plus pertinentes, évite multicolinéarité)
FEATURES = [
    "revenu_median",
    "taux_pauvrete",
    "pct_diplomes_sup",
    "pct_sans_diplome",
    "pct_cadres",
    "pct_ouvriers",
    "pct_employes",
    "pct_agriculteurs",
    "pct_proprietaires",
    "pct_hlm",
    "pct_res_secondaires",
    "pct_logements_vacants",
    "taux_chomage",
    "pct_etrangers",
    "pct_60plus",
    "pct_jeunes",
    "taux_fibre",
    "apl_medecins",
    "equipements_total_1000hab",
    "taux_delinquance_1000",
    "loyer_median",
]

MIN_POP = 200  # Filtrer les micro-communes pour stabilité statistique


def build_dataset(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Construit le dataset features + targets depuis DuckDB."""
    all_vars = list(set(FEATURES + TARGETS))
    placeholders = ",".join(["?"] * len(all_vars))

    data = con.execute(
        f"""
        SELECT code_commune, variable_id, value
        FROM commune_data
        WHERE variable_id IN ({placeholders})
        """,
        all_vars,
    ).fetchdf()

    wide = data.pivot(index="code_commune", columns="variable_id", values="value")

    # Joindre info communes
    communes = con.execute(
        "SELECT code_commune, libelle, code_departement, population FROM communes WHERE population >= ?",
        [MIN_POP],
    ).fetchdf()
    wide = wide.merge(communes, on="code_commune", how="inner")

    logger.info("Dataset régression : %d communes (pop ≥ %d)", len(wide), MIN_POP)
    return wide


def fit_ols(df: pd.DataFrame, target: str) -> dict | None:
    """Entraîne un OLS et retourne coefficients, R², résidus."""
    import statsmodels.api as sm

    available_features = [f for f in FEATURES if f in df.columns]
    sub = df[["code_commune", "libelle", "code_departement", "population", target] + available_features].dropna()

    if len(sub) < 100:
        logger.warning("[%s] Pas assez de données (%d communes)", target, len(sub))
        return None

    X = sub[available_features].values
    y = sub[target].values

    # Standardiser les features pour comparer les coefficients
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_with_const = sm.add_constant(X_scaled)
    model = sm.OLS(y, X_with_const).fit()

    # Coefficients standardisés (beta)
    coefficients = []
    # Intercept (constante)
    coefficients.append({
        "target": target,
        "feature": "_intercept",
        "beta": round(model.params[0], 4),
        "std_err": round(model.bse[0], 4),
        "t_stat": round(model.tvalues[0], 2),
        "p_value": model.pvalues[0],
    })
    for i, feat in enumerate(available_features):
        coefficients.append({
            "target": target,
            "feature": feat,
            "beta": round(model.params[i + 1], 4),
            "std_err": round(model.bse[i + 1], 4),
            "t_stat": round(model.tvalues[i + 1], 2),
            "p_value": model.pvalues[i + 1],
        })

    # Stats de normalisation (pour le simulateur front-end)
    scaler_stats = []
    for i, feat in enumerate(available_features):
        scaler_stats.append({
            "target": target,
            "feature": feat,
            "feature_mean": round(scaler.mean_[i], 4),
            "feature_std": round(scaler.scale_[i], 4),
        })

    # Résidus
    sub = sub.copy()
    sub["predicted"] = model.predict(X_with_const)
    sub["residual"] = sub[target] - sub["predicted"]
    sub["residual_std"] = sub["residual"] / sub["residual"].std()

    residuals = sub[["code_commune", "residual", "residual_std", "predicted"]].copy()
    residuals["target"] = target

    return {
        "target": target,
        "r_squared": round(model.rsquared, 4),
        "adj_r_squared": round(model.rsquared_adj, 4),
        "n_obs": len(sub),
        "n_features": len(available_features),
        "coefficients": pd.DataFrame(coefficients),
        "scaler_stats": pd.DataFrame(scaler_stats),
        "residuals": residuals,
        "aic": round(model.aic, 1),
        "bic": round(model.bic, 1),
    }


def save_to_db(results: list[dict], con: duckdb.DuckDBPyConnection) -> None:
    """Sauvegarde les résultats de régression dans DuckDB."""
    # Table des coefficients
    con.execute("""
        CREATE TABLE IF NOT EXISTS regression_results (
            target VARCHAR,
            feature VARCHAR,
            beta DOUBLE,
            std_err DOUBLE,
            t_stat DOUBLE,
            p_value DOUBLE,
            r_squared DOUBLE,
            adj_r_squared DOUBLE,
            n_obs INTEGER,
            PRIMARY KEY (target, feature)
        )
    """)
    con.execute("DELETE FROM regression_results")

    for res in results:
        coefs = res["coefficients"].copy()
        coefs["r_squared"] = res["r_squared"]
        coefs["adj_r_squared"] = res["adj_r_squared"]
        coefs["n_obs"] = res["n_obs"]
        con.register("coefs_df", coefs)
        con.execute("INSERT INTO regression_results SELECT * FROM coefs_df")
        con.unregister("coefs_df")

    # Table des stats de normalisation (pour le simulateur)
    con.execute("""
        CREATE TABLE IF NOT EXISTS regression_scaler (
            target VARCHAR,
            feature VARCHAR,
            feature_mean DOUBLE,
            feature_std DOUBLE,
            PRIMARY KEY (target, feature)
        )
    """)
    con.execute("DELETE FROM regression_scaler")

    all_stats = pd.concat([r["scaler_stats"] for r in results], ignore_index=True)
    con.register("stats_df", all_stats)
    con.execute("INSERT INTO regression_scaler SELECT * FROM stats_df")
    con.unregister("stats_df")

    # Table des résidus
    con.execute("""
        CREATE TABLE IF NOT EXISTS commune_residuals (
            code_commune VARCHAR,
            target VARCHAR,
            residual DOUBLE,
            residual_std DOUBLE,
            predicted DOUBLE,
            PRIMARY KEY (code_commune, target)
        )
    """)
    con.execute("DELETE FROM commune_residuals")

    all_residuals = pd.concat([r["residuals"] for r in results], ignore_index=True)
    # Réordonner pour matcher le schéma
    all_residuals = all_residuals[["code_commune", "target", "residual", "residual_std", "predicted"]]
    con.register("resid_df", all_residuals)
    con.execute("INSERT INTO commune_residuals SELECT * FROM resid_df")
    con.unregister("resid_df")

    logger.info(
        "%d modèles, %d coefficients, %d résidus sauvegardés",
        len(results),
        sum(len(r["coefficients"]) for r in results),
        len(all_residuals),
    )


def run() -> list[dict]:
    """Point d'entrée principal."""
    con = duckdb.connect(str(DB_PATH))
    try:
        df = build_dataset(con)

        results = []
        for target in TARGETS:
            if target not in df.columns:
                logger.warning("[%s] Variable absente", target)
                continue
            res = fit_ols(df, target)
            if res:
                results.append(res)

        if not results:
            logger.warning("Aucun modèle entraîné")
            return []

        save_to_db(results, con)

        # Affichage
        print("\n" + "=" * 90)
        print("RÉGRESSION MULTIVARIÉE — Scores électoraux ~ profil socio-éco")
        print("=" * 90)

        for res in results:
            print(f"\n{'─' * 90}")
            print(f"  {res['target']}  (R²={res['r_squared']:.3f}, R²adj={res['adj_r_squared']:.3f}, n={res['n_obs']})")
            print(f"{'─' * 90}")

            # Top features par |beta|
            coefs = res["coefficients"].copy()
            coefs["abs_beta"] = coefs["beta"].abs()
            top = coefs.nlargest(8, "abs_beta")
            for _, row in top.iterrows():
                sig = "***" if row["p_value"] < 0.001 else "** " if row["p_value"] < 0.01 else "*  " if row["p_value"] < 0.05 else "   "
                sign = "+" if row["beta"] > 0 else ""
                print(f"    {sig} {sign}{row['beta']:+.3f}  {row['feature']}")

        # Top anomalies (résidus les plus extrêmes pour ED)
        ed_target = "score_extreme_droite_pres22t1"
        ed_results = [r for r in results if r["target"] == ed_target]
        if ed_results:
            resid = ed_results[0]["residuals"]
            communes_info = con.execute(
                "SELECT code_commune, libelle, population FROM communes"
            ).fetchdf()
            resid = resid.merge(communes_info, on="code_commune", how="left")

            # Filtrer pop > 2000 pour des résultats pertinents
            resid_big = resid[resid["population"] >= 2000].copy()

            print(f"\n{'=' * 90}")
            print(f"COMMUNES SURPRENANTES — {ed_target}")
            print(f"  (résidus les plus extrêmes, pop ≥ 2000)")
            print(f"{'=' * 90}")

            # Vote ED plus fort que prédit
            top_pos = resid_big.nlargest(15, "residual_std")
            print("\n  ED plus fort que prédit par le profil socio-éco :")
            for _, row in top_pos.iterrows():
                print(f"    +{row['residual_std']:+.1f}σ  {row['libelle']:30s} (pop={row['population']:.0f})")

            # Vote ED plus faible que prédit
            top_neg = resid_big.nsmallest(15, "residual_std")
            print("\n  ED plus faible que prédit par le profil socio-éco :")
            for _, row in top_neg.iterrows():
                print(f"    {row['residual_std']:+.1f}σ  {row['libelle']:30s} (pop={row['population']:.0f})")

        return results
    finally:
        con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
