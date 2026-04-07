"""Transformer IPS : moyenne pondérée par commune."""

import pandas as pd


def transform(df: pd.DataFrame, source: dict) -> pd.DataFrame:
    # Colonnes : code_insee_de_la_commune, ips, rentree_scolaire
    df = df.rename(columns={"code_insee_de_la_commune": "code_commune"})

    from pipeline.transformers import remap_arrondissements

    df = remap_arrondissements(df, col="code_commune")

    # Garder la dernière rentrée disponible
    if "rentree_scolaire" in df.columns:
        derniere = df["rentree_scolaire"].max()
        df = df[df["rentree_scolaire"] == derniere]

    # Moyenne IPS par commune
    df["ips"] = pd.to_numeric(df["ips"], errors="coerce")
    ips_mean = df.groupby("code_commune")["ips"].mean().reset_index()

    # Déterminer le nom de variable selon la source
    source_id = source["id"]
    if "ecole" in source_id:
        ips_mean = ips_mean.rename(columns={"ips": "ips_ecoles"})
    elif "college" in source_id:
        ips_mean = ips_mean.rename(columns={"ips": "ips_colleges"})

    return ips_mean
