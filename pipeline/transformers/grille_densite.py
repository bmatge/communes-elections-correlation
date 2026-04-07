"""Transformer grille_densite — nettoyage du fichier INSEE DEGURBA."""

import pandas as pd


def transform(df: pd.DataFrame, source: dict) -> pd.DataFrame:
    # Nettoyer les noms de colonnes (retirer \n, strip)
    df.columns = [c.replace("\n", " ").strip() for c in df.columns]

    # Renommer les colonnes utiles
    cols = list(df.columns)
    rename = {cols[0]: "CODGEO", cols[2]: "DEGURBA"}
    df = df.rename(columns=rename)

    # Pad CODGEO sur 5 caractères
    df["CODGEO"] = df["CODGEO"].astype(str).str.zfill(5)

    # Convertir DEGURBA en str (variable catégorielle)
    df["DEGURBA"] = df["DEGURBA"].astype(str)

    return df[["CODGEO", "DEGURBA"]].copy()
