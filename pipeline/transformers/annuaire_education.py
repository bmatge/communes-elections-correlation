"""Transformer annuaire éducation : comptage d'établissements par commune."""

import pandas as pd


def transform(df: pd.DataFrame, source: dict) -> pd.DataFrame:
    # Colonnes : code_commune (dans le dataset : code_commune ou similaire)
    # type_etablissement : Ecole, Collège, Lycée, etc.

    col_commune = None
    for c in ["code_commune", "code_commune_de_l_etablissement", "code_postal"]:
        if c in df.columns:
            col_commune = c
            break

    if col_commune is None:
        # Chercher une colonne qui ressemble à un code commune
        for c in df.columns:
            if "commune" in c.lower() and "code" in c.lower():
                col_commune = c
                break

    if col_commune is None:
        return df

    df = df.rename(columns={col_commune: "code_commune"})

    from pipeline.transformers import remap_arrondissements

    df = remap_arrondissements(df, col="code_commune")

    # Catégoriser les types d'établissements
    type_col = "type_etablissement"
    if type_col not in df.columns:
        return df

    df["is_ecole"] = df[type_col].str.contains("cole", case=False, na=False).astype(int)
    df["is_college"] = df[type_col].str.contains("Coll", case=False, na=False).astype(int)
    df["is_lycee"] = df[type_col].str.contains("Lyc", case=False, na=False).astype(int)

    counts = df.groupby("code_commune").agg(
        nb_ecoles=("is_ecole", "sum"),
        nb_colleges=("is_college", "sum"),
        nb_lycees=("is_lycee", "sum"),
        nb_etablissements=("code_commune", "count"),
    ).reset_index()

    return counts
