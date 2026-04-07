"""Transformer APL : accessibilité aux médecins généralistes par commune."""

import pandas as pd


def transform(df: pd.DataFrame, source: dict) -> pd.DataFrame:
    from pipeline.config import raw_path_for_source

    path = raw_path_for_source(source)

    # Lire la feuille APL 2023, skip 8 lignes de headers
    df = pd.read_excel(path, sheet_name="APL 2023", skiprows=8, engine="openpyxl", header=None)

    # Les colonnes sont : code_commune, commune, APL, APL_65, APL_62, APL_60, pop_std, pop_totale
    df.columns = [
        "code_commune", "commune", "apl_medecins", "apl_medecins_65",
        "apl_medecins_62", "apl_medecins_60", "pop_standardisee", "pop_totale",
    ]

    # Garder seulement l'APL principal et convertir
    df["code_commune"] = df["code_commune"].astype(str).str.zfill(5)

    from pipeline.transformers import remap_arrondissements

    df = remap_arrondissements(df, col="code_commune")

    df["apl_medecins"] = pd.to_numeric(df["apl_medecins"], errors="coerce")

    # Moyenne pondérée pour les arrondissements agrégés (PLM)
    result = df.groupby("code_commune", as_index=False)["apl_medecins"].mean()

    return result.dropna(subset=["apl_medecins"])
