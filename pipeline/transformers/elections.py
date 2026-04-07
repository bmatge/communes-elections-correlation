"""Transformer pour les résultats électoraux agrégés.

Traite les fichiers elections_agregees_general et elections_agregees_candidats.
Agrège par commune et calcule les scores par famille politique.
"""

import logging

import pandas as pd

from pipeline.config import get_familles_politiques

logger = logging.getLogger(__name__)

# Mapping candidats présidentiels → famille politique
CANDIDATS_PRES_2022 = {
    "MACRON": "centre",
    "LE PEN": "extreme_droite",
    "MÉLENCHON": "gauche",
    "ZEMMOUR": "extreme_droite",
    "PÉCRESSE": "droite",
    "JADOT": "gauche",
    "LASSALLE": "sans_etiquette",
    "ROUSSEL": "gauche",
    "DUPONT-AIGNAN": "droite",
    "HIDALGO": "gauche",
    "POUTOU": "gauche",
    "ARTHAUD": "gauche",
}

CANDIDATS_PRES_2017 = {
    "MACRON": "centre",
    "LE PEN": "extreme_droite",
    "FILLON": "droite",
    "MÉLENCHON": "gauche",
    "HAMON": "gauche",
    "DUPONT-AIGNAN": "droite",
    "LASSALLE": "sans_etiquette",
    "POUTOU": "gauche",
    "ARTHAUD": "gauche",
    "ASSELINEAU": "sans_etiquette",
    "CHEMINADE": "sans_etiquette",
}


def _build_nuance_to_famille() -> dict[str, str]:
    """Mapping nuance → famille (inversé depuis la config)."""
    familles = get_familles_politiques()
    mapping = {}
    for famille, nuances in familles.items():
        for nuance in nuances:
            mapping[nuance] = famille
    return mapping


def _assign_famille(row: pd.Series, nuance_map: dict, candidat_map: dict) -> str:
    """Assigne une famille politique via nuance ou nom du candidat."""
    nuance = row.get("nuance")
    if pd.notna(nuance) and nuance in nuance_map:
        return nuance_map[nuance]
    nom = row.get("nom")
    if pd.notna(nom) and nom in candidat_map:
        return candidat_map[nom]
    return "autres"


def transform(df: pd.DataFrame, source: dict) -> pd.DataFrame:
    source_id = source["id"]

    if source_id == "elections_agregees_general":
        return _transform_general(df, source)
    elif source_id == "elections_agregees_candidats":
        return _transform_candidats(df, source)
    else:
        logger.warning("[%s] Source non reconnue par le transformer elections", source_id)
        return df


def _transform_general(df: pd.DataFrame, source: dict) -> pd.DataFrame:
    """Agrège les résultats généraux par commune et par élection."""
    # Filtrer les élections demandées
    elections = source.get("filter", {}).get("id_election", [])
    if elections:
        df = df[df["id_election"].isin(elections)]

    # Agréger par commune + élection (somme des bureaux de vote)
    agg = df.groupby(["id_election", "code_commune"]).agg(
        inscrits=("inscrits", "sum"),
        abstentions=("abstentions", "sum"),
        votants=("votants", "sum"),
        blancs=("blancs", "sum"),
        nuls=("nuls", "sum"),
        exprimes=("exprimes", "sum"),
    ).reset_index()

    # Calculer les taux
    agg["pct_abstention"] = agg["abstentions"] / agg["inscrits"] * 100
    agg["pct_participation"] = agg["votants"] / agg["inscrits"] * 100

    logger.info("[elections_general] %d communes × %d élections", agg["code_commune"].nunique(), agg["id_election"].nunique())

    # Pivoter : une ligne par commune, une colonne par élection + indicateur
    results = []
    for election_id in agg["id_election"].unique():
        sub = agg[agg["id_election"] == election_id].copy()
        suffix = _election_suffix(election_id)

        renamed = sub[["code_commune"]].copy()
        renamed[f"inscrits_{suffix}"] = sub["inscrits"].values
        renamed[f"pct_abstention_{suffix}"] = sub["pct_abstention"].values
        renamed[f"pct_participation_{suffix}"] = sub["pct_participation"].values
        results.append(renamed)

    # Joindre toutes les élections
    if not results:
        return pd.DataFrame()

    merged = results[0]
    for r in results[1:]:
        merged = merged.merge(r, on="code_commune", how="outer")

    return merged


def _transform_candidats(df: pd.DataFrame, source: dict) -> pd.DataFrame:
    """Agrège les voix par famille politique par commune et par élection."""
    elections = source.get("filter", {}).get("id_election", [])
    if elections:
        df = df[df["id_election"].isin(elections)]

    nuance_map = _build_nuance_to_famille()

    # Mapping candidat par élection
    candidat_maps = {
        "2022_pres_t1": CANDIDATS_PRES_2022,
        "2017_pres_t1": CANDIDATS_PRES_2017,
    }

    # Stratégie par type de scrutin :
    # - Présidentielles : mapping par nom de candidat (pas de nuance fiable)
    # - Municipales : seulement les lignes avec nuance (scrutin de liste, ~3K communes)
    # - Législatives, Européennes, Régionales, Départementales : toutes les lignes ont une nuance
    frames = []
    for election_id in df["id_election"].unique():
        sub = df[df["id_election"] == election_id].copy()
        cand_map = candidat_maps.get(election_id, {})

        if "pres" in election_id:
            # Présidentielle : toutes les lignes, mapping par nom
            sub["famille"] = sub.apply(lambda r: _assign_famille(r, nuance_map, cand_map), axis=1)
            frames.append(sub)
        elif "muni" in election_id:
            # Municipales : seulement les lignes avec nuance (scrutin de liste)
            nuanced = sub[sub["nuance"].notna()].copy()
            nuanced["famille"] = nuanced["nuance"].map(nuance_map).fillna("autres")
            frames.append(nuanced)
        else:
            # Législatives, Européennes, Régionales, Départementales : toutes ont une nuance
            sub["famille"] = sub["nuance"].map(nuance_map).fillna("autres")
            frames.append(sub)

    if not frames:
        return pd.DataFrame()

    df_nuanced = pd.concat(frames, ignore_index=True)

    # Agréger voix par commune + élection + famille
    agg = df_nuanced.groupby(["id_election", "code_commune", "famille"]).agg(
        voix=("voix", "sum"),
    ).reset_index()

    # Calculer le total des voix exprimées par commune + élection
    total_voix = agg.groupby(["id_election", "code_commune"])["voix"].sum().reset_index()
    total_voix = total_voix.rename(columns={"voix": "total_voix"})

    agg = agg.merge(total_voix, on=["id_election", "code_commune"])
    agg["pct"] = agg["voix"] / agg["total_voix"] * 100

    # Compter le nombre de listes par commune
    nb_listes = df_nuanced.groupby(["id_election", "code_commune"])["no_panneau"].nunique().reset_index()
    nb_listes = nb_listes.rename(columns={"no_panneau": "nb_listes"})

    logger.info("[elections_candidats] %d communes avec nuances", agg["code_commune"].nunique())

    # Pivoter : une ligne par commune
    results = []
    familles = ["gauche", "centre", "droite", "extreme_droite", "sans_etiquette", "autres"]

    for election_id in agg["id_election"].unique():
        sub = agg[agg["id_election"] == election_id]
        suffix = _election_suffix(election_id)

        # Pivoter familles → colonnes
        pivot = sub.pivot_table(
            index="code_commune",
            columns="famille",
            values="pct",
            fill_value=0,
        ).reset_index()

        # Renommer les colonnes
        renamed = pivot[["code_commune"]].copy()
        for fam in familles:
            col_name = f"score_{fam}_{suffix}"
            if fam in pivot.columns:
                renamed[col_name] = pivot[fam].values
            else:
                renamed[col_name] = 0.0

        # Axe gauche-droite continu (0 = gauche, 1 = droite+ED)
        renamed[f"axe_gd_{suffix}"] = (
            renamed.get(f"score_droite_{suffix}", 0) +
            renamed.get(f"score_extreme_droite_{suffix}", 0)
        ) / 100.0

        # Nombre de listes
        nl = nb_listes[nb_listes["id_election"] == election_id][["code_commune", "nb_listes"]]
        nl = nl.rename(columns={"nb_listes": f"nb_listes_{suffix}"})
        renamed = renamed.merge(nl, on="code_commune", how="left")

        results.append(renamed)

    if not results:
        return pd.DataFrame()

    merged = results[0]
    for r in results[1:]:
        merged = merged.merge(r, on="code_commune", how="outer")

    return merged


def _election_suffix(election_id: str) -> str:
    """Convertit un id_election en suffixe court pour les noms de colonnes."""
    mapping = {
        "2026_muni_t1": "muni26t1",
        "2026_muni_t2": "muni26t2",
        "2020_muni_t1": "muni20t1",
        "2020_muni_t2": "muni20t2",
        "2022_pres_t1": "pres22t1",
        "2017_pres_t1": "pres17t1",
        "2024_legi_t1": "legi24t1",
        "2022_legi_t1": "legi22t1",
        "2024_euro_t1": "euro24t1",
        "2021_regi_t1": "regi21t1",
        "2021_dpmt_t1": "dpmt21t1",
    }
    return mapping.get(election_id, election_id.replace("_", ""))
