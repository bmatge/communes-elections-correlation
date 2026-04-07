"""Transformer fibre : taux de couverture FTTH par commune."""

import pandas as pd


def transform(df: pd.DataFrame, source: dict) -> pd.DataFrame:
    df = df.rename(columns={"insee_com": "code_commune"})

    # locaux_ftth / locaux_arcep = taux de couverture
    df["locaux_ftth"] = pd.to_numeric(df.get("locaux_ftth"), errors="coerce")
    df["locaux_arcep"] = pd.to_numeric(df.get("locaux_arcep"), errors="coerce")

    df["taux_fibre"] = (df["locaux_ftth"] / df["locaux_arcep"] * 100).round(1)

    result = df[["code_commune", "taux_fibre"]].dropna(subset=["code_commune"])
    # Dédupliquer (certaines communes ont plusieurs lignes par opérateur/trimestre)
    result = result.groupby("code_commune")["taux_fibre"].mean().round(1).reset_index()
    return result
