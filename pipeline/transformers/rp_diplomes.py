"""Transformer rp_diplomes — agrégation IRIS → commune (RP 2021)."""

import pandas as pd

from pipeline.transformers import remap_arrondissements


def transform(df: pd.DataFrame, source: dict) -> pd.DataFrame:
    # Colonnes numériques à agréger (tout sauf identifiants IRIS)
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

    # La colonne P21_NSCOL15P_NODIP n'existe pas directement dans ce fichier.
    # Il faut la recalculer : sans diplôme = DIPLMIN (diplôme minimum = aucun ou CEP)
    if "P21_NSCOL15P_DIPLMIN" in agg.columns and "P21_NSCOL15P_NODIP" not in agg.columns:
        agg = agg.rename(columns={"P21_NSCOL15P_DIPLMIN": "P21_NSCOL15P_NODIP"})

    return agg
