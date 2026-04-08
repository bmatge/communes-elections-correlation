"""D2 — Décalage local/national.

Compare le vote municipal 2026 au vote aux élections nationales (pres22, euro24, legi24)
pour les ~3.3K communes qui ont les deux. Stocke le gap dans DuckDB.
"""

import logging

import duckdb
import pandas as pd

from pipeline.config import DB_PATH

logger = logging.getLogger(__name__)

# Familles politiques communes à toutes les élections
FAMILLES = ["gauche", "droite", "extreme_droite", "centre"]

# Paires de comparaison : (muni, national)
COMPARAISONS = [
    ("muni26t1", "pres22t1"),
    ("muni26t1", "euro24t1"),
    ("muni26t1", "legi24t1"),
]


def compute_decalage(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Calcule le décalage muni vs national pour chaque famille et scrutin."""
    all_rows = []

    for famille in FAMILLES:
        for muni_suffix, nat_suffix in COMPARAISONS:
            muni_var = f"score_{famille}_{muni_suffix}"
            nat_var = f"score_{famille}_{nat_suffix}"

            rows = con.execute(
                """
                SELECT m.code_commune,
                       m.value AS score_muni,
                       n.value AS score_national
                FROM commune_data m
                JOIN commune_data n ON m.code_commune = n.code_commune
                WHERE m.variable_id = ? AND n.variable_id = ?
                """,
                [muni_var, nat_var],
            ).fetchdf()

            if rows.empty:
                continue

            rows["decalage"] = (rows["score_muni"] - rows["score_national"]).round(2)
            rows["famille"] = famille
            rows["scrutin_muni"] = muni_suffix
            rows["scrutin_national"] = nat_suffix

            all_rows.append(
                rows[["code_commune", "famille", "scrutin_muni", "scrutin_national",
                       "score_muni", "score_national", "decalage"]]
            )

    if not all_rows:
        return pd.DataFrame()

    result = pd.concat(all_rows, ignore_index=True)
    logger.info(
        "Décalage calculé : %d lignes, %d communes",
        len(result), result["code_commune"].nunique()
    )
    return result


def save_to_db(df: pd.DataFrame, con: duckdb.DuckDBPyConnection) -> None:
    """Sauvegarde les décalages dans DuckDB."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS decalage_local_national (
            code_commune VARCHAR,
            famille VARCHAR,
            scrutin_muni VARCHAR,
            scrutin_national VARCHAR,
            score_muni DOUBLE,
            score_national DOUBLE,
            decalage DOUBLE,
            PRIMARY KEY (code_commune, famille, scrutin_national)
        )
    """)
    con.execute("DELETE FROM decalage_local_national")
    con.register("dec_df", df)
    con.execute("INSERT INTO decalage_local_national SELECT * FROM dec_df")
    con.unregister("dec_df")
    logger.info("%d décalages sauvegardés", len(df))


def run() -> pd.DataFrame:
    """Point d'entrée principal."""
    con = duckdb.connect(str(DB_PATH))
    try:
        df = compute_decalage(con)
        if df.empty:
            logger.warning("Aucun décalage calculé")
            return df

        save_to_db(df, con)

        # Affichage des communes les plus décalées
        communes = con.execute(
            "SELECT code_commune, libelle, population FROM communes"
        ).fetchdf()
        df = df.merge(communes, on="code_commune", how="left")

        print("\n" + "=" * 90)
        print("DÉCALAGE LOCAL / NATIONAL — Municipales 2026 vs élections nationales")
        print("=" * 90)

        # Focus ED vs pres22
        ed = df[(df["famille"] == "extreme_droite") & (df["scrutin_national"] == "pres22t1")].copy()
        ed = ed[ed["population"] >= 5000]

        if not ed.empty:
            print(f"\n{'─' * 90}")
            print("  ED : communes où le score municipal >> score présidentiel")
            print(f"{'─' * 90}")
            top = ed.nlargest(10, "decalage")
            for _, row in top.iterrows():
                print(f"    +{row['decalage']:+.1f}pp  {row['libelle']:30s} "
                      f"(muni={row['score_muni']:.1f}%, pres={row['score_national']:.1f}%)")

            print(f"\n  ED : communes où le score municipal << score présidentiel")
            bot = ed.nsmallest(10, "decalage")
            for _, row in bot.iterrows():
                print(f"    {row['decalage']:+.1f}pp  {row['libelle']:30s} "
                      f"(muni={row['score_muni']:.1f}%, pres={row['score_national']:.1f}%)")

        # Focus gauche vs pres22
        ga = df[(df["famille"] == "gauche") & (df["scrutin_national"] == "pres22t1")].copy()
        ga = ga[ga["population"] >= 5000]

        if not ga.empty:
            print(f"\n{'─' * 90}")
            print("  Gauche : communes où le score municipal >> score présidentiel")
            print(f"{'─' * 90}")
            top = ga.nlargest(10, "decalage")
            for _, row in top.iterrows():
                print(f"    +{row['decalage']:+.1f}pp  {row['libelle']:30s} "
                      f"(muni={row['score_muni']:.1f}%, pres={row['score_national']:.1f}%)")

        return df
    finally:
        con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
