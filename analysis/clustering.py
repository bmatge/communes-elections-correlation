"""B4 — Clustering et ACP des communes.

Identifie des profils-types de communes (rural aisé, périurbain précaire,
urbain bobo...) et leur signature électorale.

1. ACP sur les variables socio-éco → réduction de dimension
2. K-Means sur les composantes principales → clusters de communes
3. Caractérisation des clusters par moyennes et signature électorale

Résultats stockés dans DuckDB :
- `commune_clusters` : cluster assigné à chaque commune
- `cluster_profiles` : profil moyen de chaque cluster
- `pca_loadings` : loadings des axes principaux
"""

import logging

import duckdb
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from pipeline.config import DB_PATH

logger = logging.getLogger(__name__)

# Variables socio-éco pour le clustering (sélection)
CLUSTER_FEATURES = [
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
    "equipements_total_1000hab",
]

# Variables électorales pour la signature (pas en features du clustering)
ELECTORAL_SIGNATURE = [
    "score_gauche_pres22t1",
    "score_droite_pres22t1",
    "score_extreme_droite_pres22t1",
    "score_centre_pres22t1",
    "pct_abstention_pres22t1",
    "score_gauche_euro24t1",
    "score_extreme_droite_euro24t1",
    "pct_abstention_euro24t1",
]

N_CLUSTERS = 8
N_COMPONENTS = 6
MIN_POP = 200


def build_dataset(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Construit le dataset pour le clustering."""
    all_vars = list(set(CLUSTER_FEATURES + ELECTORAL_SIGNATURE))
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

    communes = con.execute(
        "SELECT code_commune, libelle, code_departement, code_region, population, densite FROM communes WHERE population >= ?",
        [MIN_POP],
    ).fetchdf()
    wide = wide.merge(communes, on="code_commune", how="inner")

    logger.info("Dataset clustering : %d communes", len(wide))
    return wide


def run_pca(df: pd.DataFrame) -> tuple[np.ndarray, PCA, StandardScaler, list[str]]:
    """ACP sur les variables socio-éco."""
    available = [f for f in CLUSTER_FEATURES if f in df.columns]
    sub = df[available].dropna()
    valid_idx = sub.index

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(sub)

    pca = PCA(n_components=min(N_COMPONENTS, len(available)))
    X_pca = pca.fit_transform(X_scaled)

    logger.info(
        "ACP : %d composantes, variance expliquée : %s (total: %.1f%%)",
        pca.n_components_,
        [f"{v:.1%}" for v in pca.explained_variance_ratio_],
        100 * sum(pca.explained_variance_ratio_),
    )

    return X_pca, pca, scaler, available, valid_idx


def run_kmeans(X_pca: np.ndarray) -> np.ndarray:
    """K-Means sur les composantes principales."""
    kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=20)
    labels = kmeans.fit_predict(X_pca)
    logger.info(
        "K-Means : %d clusters, inertie = %.0f",
        N_CLUSTERS, kmeans.inertia_,
    )
    return labels


def characterize_clusters(
    df: pd.DataFrame, labels: np.ndarray, valid_idx, features: list[str]
) -> pd.DataFrame:
    """Calcule le profil moyen de chaque cluster (socio-éco + électoral)."""
    sub = df.loc[valid_idx].copy()
    sub["cluster"] = labels

    all_vars = features + [v for v in ELECTORAL_SIGNATURE if v in sub.columns]
    all_vars.append("population")

    profiles = sub.groupby("cluster")[all_vars].mean().round(2)
    profiles["n_communes"] = sub.groupby("cluster").size()

    return profiles


def label_clusters(profiles: pd.DataFrame) -> dict[int, str]:
    """Attribue un label descriptif à chaque cluster basé sur son profil."""
    labels = {}
    for cluster_id in profiles.index:
        p = profiles.loc[cluster_id]
        parts = []

        # Urbanité
        if p.get("population", 0) > 50000:
            parts.append("Métropole")
        elif p.get("population", 0) > 10000:
            parts.append("Urbain")
        elif p.get("population", 0) > 2000:
            parts.append("Périurbain")
        else:
            parts.append("Rural")

        # Revenus
        med_rev = profiles["revenu_median"].median() if "revenu_median" in profiles else 0
        if p.get("revenu_median", 0) > med_rev * 1.15:
            parts.append("aisé")
        elif p.get("revenu_median", 0) < med_rev * 0.85:
            parts.append("modeste")

        # CSP dominante
        if p.get("pct_cadres", 0) > profiles["pct_cadres"].median() * 1.5:
            parts.append("cadres")
        elif p.get("pct_ouvriers", 0) > profiles["pct_ouvriers"].median() * 1.3:
            parts.append("ouvrier")
        elif p.get("pct_agriculteurs", 0) > profiles["pct_agriculteurs"].median() * 1.5:
            parts.append("agricole")
        elif p.get("pct_60plus", 0) > profiles["pct_60plus"].median() * 1.2:
            parts.append("retraités")

        labels[cluster_id] = " ".join(parts) if parts else f"Cluster {cluster_id}"

    return labels


def save_to_db(
    df: pd.DataFrame, labels: np.ndarray, valid_idx,
    profiles: pd.DataFrame, pca: PCA, features: list[str],
    cluster_labels: dict[int, str],
    con: duckdb.DuckDBPyConnection,
) -> None:
    """Sauvegarde les résultats dans DuckDB."""
    # Commune → cluster
    sub = df.loc[valid_idx, ["code_commune"]].copy()
    sub["cluster_id"] = labels
    sub["cluster_label"] = sub["cluster_id"].map(cluster_labels)

    con.execute("""
        CREATE TABLE IF NOT EXISTS commune_clusters (
            code_commune VARCHAR PRIMARY KEY,
            cluster_id INTEGER,
            cluster_label VARCHAR
        )
    """)
    con.execute("DELETE FROM commune_clusters")
    con.register("clusters_df", sub)
    con.execute("INSERT INTO commune_clusters SELECT * FROM clusters_df")
    con.unregister("clusters_df")

    # Profils
    profiles_long = profiles.reset_index()
    profiles_long["cluster_label"] = profiles_long["cluster"].map(cluster_labels)

    con.execute("""
        CREATE TABLE IF NOT EXISTS cluster_profiles (
            cluster_id INTEGER,
            cluster_label VARCHAR,
            variable VARCHAR,
            value DOUBLE
        )
    """)
    con.execute("DELETE FROM cluster_profiles")
    # Melt le profil
    value_cols = [c for c in profiles_long.columns if c not in ("cluster", "cluster_label")]
    melted = profiles_long.melt(
        id_vars=["cluster", "cluster_label"],
        value_vars=value_cols,
        var_name="variable",
    )
    melted = melted.rename(columns={"cluster": "cluster_id"})
    melted = melted[["cluster_id", "cluster_label", "variable", "value"]]
    con.register("profiles_df", melted)
    con.execute("INSERT INTO cluster_profiles SELECT * FROM profiles_df")
    con.unregister("profiles_df")

    # PCA loadings
    loadings = pd.DataFrame(
        pca.components_.T,
        columns=[f"PC{i+1}" for i in range(pca.n_components_)],
        index=features,
    )
    loadings = loadings.reset_index().rename(columns={"index": "feature"})
    loadings_long = loadings.melt(id_vars="feature", var_name="component", value_name="loading")

    con.execute("""
        CREATE TABLE IF NOT EXISTS pca_loadings (
            feature VARCHAR,
            component VARCHAR,
            loading DOUBLE,
            PRIMARY KEY (feature, component)
        )
    """)
    con.execute("DELETE FROM pca_loadings")
    con.register("loadings_df", loadings_long)
    con.execute("INSERT INTO pca_loadings SELECT * FROM loadings_df")
    con.unregister("loadings_df")

    logger.info(
        "%d communes assignées à %d clusters, %d loadings sauvegardés",
        len(sub), N_CLUSTERS, len(loadings_long),
    )


def run() -> None:
    """Point d'entrée principal."""
    con = duckdb.connect(str(DB_PATH))
    try:
        df = build_dataset(con)

        X_pca, pca, scaler, features, valid_idx = run_pca(df)
        labels = run_kmeans(X_pca)
        profiles = characterize_clusters(df, labels, valid_idx, features)
        cluster_labels = label_clusters(profiles)
        save_to_db(df, labels, valid_idx, profiles, pca, features, cluster_labels, con)

        # Affichage
        print("\n" + "=" * 100)
        print("ACP — Loadings des 3 premiers axes")
        print("=" * 100)
        for i in range(min(3, pca.n_components_)):
            var_exp = pca.explained_variance_ratio_[i]
            loadings = list(zip(features, pca.components_[i]))
            loadings.sort(key=lambda x: abs(x[1]), reverse=True)
            print(f"\n  PC{i+1} ({var_exp:.1%} variance) :")
            for feat, load in loadings[:6]:
                sign = "+" if load > 0 else ""
                print(f"    {sign}{load:+.3f}  {feat}")

        print("\n" + "=" * 100)
        print(f"CLUSTERS ({N_CLUSTERS} groupes)")
        print("=" * 100)

        for cluster_id in sorted(profiles.index):
            p = profiles.loc[cluster_id]
            label = cluster_labels[cluster_id]
            n = int(p["n_communes"])
            pop_moy = p["population"]

            print(f"\n  [{cluster_id}] {label} ({n} communes, pop moy={pop_moy:.0f})")

            # Signature socio-éco
            print("    Socio-éco :", end="")
            for feat in ["revenu_median", "pct_cadres", "pct_ouvriers", "pct_diplomes_sup", "pct_proprietaires", "pct_hlm"]:
                if feat in profiles.columns:
                    print(f"  {feat.replace('pct_', '').replace('_', ' ')}={p[feat]:.1f}", end="")
            print()

            # Signature électorale
            print("    Électoral :", end="")
            for var in ELECTORAL_SIGNATURE[:5]:
                short = var.replace("score_", "").replace("_pres22t1", "").replace("pct_", "")
                if var in profiles.columns:
                    print(f"  {short}={p[var]:.1f}%", end="")
            print()

    finally:
        con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
