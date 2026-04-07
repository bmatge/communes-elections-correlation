"""Transformer rp_activite — agrégation du TD_ACT1 par commune."""

import pandas as pd


def transform(df: pd.DataFrame, source: dict) -> pd.DataFrame:
    # Filtrer communes uniquement
    df = df[df["NIVGEO"] == "COM"].copy()

    # Convertir NB en float
    df["NB"] = pd.to_numeric(df["NB"], errors="coerce")

    # Convertir AGED65 en int pour filtrer 15-64 ans
    df["age"] = pd.to_numeric(df["AGED65"], errors="coerce")
    df = df[(df["age"] >= 15) & (df["age"] <= 64)].copy()

    # Chômeurs : TACTR_2 == 12
    chomeurs = (
        df[df["TACTR_2"] == 12]
        .groupby("CODGEO")["NB"]
        .sum()
        .rename("P21_CHOM1564")
    )

    # Actifs : TACTR_2 in (11, 12) — actifs occupés + chômeurs
    actifs = (
        df[df["TACTR_2"].isin([11, 12])]
        .groupby("CODGEO")["NB"]
        .sum()
        .rename("P21_ACT1564")
    )

    # Joindre
    result = pd.concat([actifs, chomeurs], axis=1).reset_index()

    # Pad CODGEO sur 5 caractères
    result["CODGEO"] = result["CODGEO"].astype(str).str.zfill(5)

    return result
