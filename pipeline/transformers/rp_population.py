"""Transformer rp_population — agrégation IRIS → commune (RP 2022)."""

import pandas as pd

from pipeline.transformers import remap_arrondissements


def transform(df: pd.DataFrame, source: dict) -> pd.DataFrame:
    # Colonnes numériques à agréger
    numeric_cols = [c for c in df.columns if c not in ("IRIS", "COM", "TYP_IRIS", "LAB_IRIS")]

    # Convertir en numeric
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Remapper arrondissements PLM → code commune avant agrégation
    df = remap_arrondissements(df, col="COM")

    # Grouper par COM (somme des IRIS)
    agg = df.groupby("COM")[numeric_cols].sum().reset_index()

    # Renommer COM → CODGEO
    agg = agg.rename(columns={"COM": "CODGEO"})

    # Pad CODGEO sur 5 caractères
    agg["CODGEO"] = agg["CODGEO"].astype(str).str.zfill(5)

    return agg
