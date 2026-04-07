"""Transformer RNA : nombre d'associations par commune.

Le RNA ne contient pas de code commune INSEE, seulement un code postal
et un nom de commune (libcom). La jointure nécessite une table de
correspondance code postal → code commune INSEE.

Pour l'instant, on utilise le code postal des 2 premiers caractères
comme département et on construit une jointure approximative.
TODO: utiliser la table officielle La Poste / INSEE pour une jointure exacte.
"""

import pandas as pd


def transform(df: pd.DataFrame, source: dict) -> pd.DataFrame:
    # Filtrer les associations actives
    if "nature" in df.columns:
        df = df[df["nature"].isin(["D", "R"])]

    df = df.dropna(subset=["adrs_codepostal"])
    df["adrs_codepostal"] = df["adrs_codepostal"].astype(str).str.strip().str.zfill(5)

    # Pour les communes simples, code_postal ≈ code_commune
    # SAUF pour : Paris (750XX→75056), Lyon (6900X→69381..69389), Marseille (1301X→13201..13216)
    # Et les communes à CP multiples ou partagés.
    # En première approximation, on utilise le code postal directement
    # et on note qu'il y aura ~10% de perte à la jointure.
    df["code_commune"] = df["adrs_codepostal"]

    # Corrections connues : Paris, Lyon, Marseille
    df.loc[df["code_commune"].str.startswith("7500"), "code_commune"] = "75056"
    df.loc[df["code_commune"].str.startswith("7501"), "code_commune"] = "75056"
    df.loc[df["code_commune"].str.startswith("7502"), "code_commune"] = "75056"
    df.loc[df["code_commune"].str.match(r"^6900[1-9]$"), "code_commune"] = "69123"
    df.loc[df["code_commune"].str.match(r"^1301[0-6]$"), "code_commune"] = "13055"

    # Compter par commune
    counts = df.groupby("code_commune").size().reset_index(name="nb_associations")

    return counts
