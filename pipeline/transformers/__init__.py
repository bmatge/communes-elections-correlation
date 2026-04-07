"""Utilitaires partagés entre transformers."""

import pandas as pd

# Mapping arrondissements → code commune INSEE
# Paris : 75101-75120 → 75056
# Lyon : 69381-69389 → 69123
# Marseille : 13201-13216 → 13055
PLM_ARRONDISSEMENTS = {
    **{f"7510{i}": "75056" for i in range(1, 10)},
    **{f"751{i}": "75056" for i in range(10, 21)},
    **{f"6938{i}": "69123" for i in range(1, 10)},
    **{f"1320{i}": "13055" for i in range(1, 10)},
    **{f"132{i}": "13055" for i in range(10, 17)},
}


def remap_arrondissements(df: pd.DataFrame, col: str = "COM") -> pd.DataFrame:
    """Remplace les codes arrondissements PLM par le code commune unique."""
    df[col] = df[col].astype(str).str.zfill(5)
    df[col] = df[col].replace(PLM_ARRONDISSEMENTS)
    return df
