# Architecture — VoteSocio

## Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────┐
│                     sources.yaml                            │
│  (registry déclaratif : URLs, colonnes, formules, types)    │
└────────────────────────┬────────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
   ┌────────────┐ ┌────────────┐ ┌────────────┐
   │ datagouv   │ │ insee      │ │ geojson    │
   │ downloader │ │ downloader │ │ downloader │
   └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
         │              │              │
         ▼              ▼              ▼
   ┌──────────────────────────────────────────┐
   │              data/raw/                    │
   │  (fichiers bruts : CSV, Parquet, GeoJSON) │
   └────────────────────┬─────────────────────┘
                        │
                        ▼
   ┌──────────────────────────────────────────┐
   │           02_transform.py                 │
   │  1. Mapping colonnes (depuis YAML)        │
   │  2. Calcul ratios (formules YAML)         │
   │  3. Transformer custom (optionnel)        │
   └────────────────────┬─────────────────────┘
                        │
                        ▼
   ┌──────────────────────────────────────────┐
   │              03_load.py                   │
   │  → INSERT dans commune_data              │
   │  → INSERT dans variables_meta            │
   │  → REBUILD vue communes_wide             │
   └────────────────────┬─────────────────────┘
                        │
                        ▼
   ┌──────────────────────────────────────────┐
   │           db/votesocio.duckdb             │
   │                                           │
   │  communes          (table pivot)          │
   │  variables_meta     (registre)            │
   │  commune_data       (EAV numérique)       │
   │  commune_data_cat   (EAV catégoriel)      │
   │  elections_raw      (détail par liste)     │
   │  communes_wide      (vue pivotée)         │
   │  geo_communes       (géométries)          │
   └────────────────────┬─────────────────────┘
                        │
              ┌─────────┼─────────┐
              ▼                   ▼
   ┌──────────────────┐  ┌──────────────────┐
   │  04_analyze.py   │  │    web/           │
   │  - Corrélations  │  │  - Fiche commune  │
   │  - ACP           │  │  - Comparateur    │
   │  - Régression    │  │  - Simulateur     │
   │  - Anomalies     │  │  - Carte          │
   └──────────────────┘  └──────────────────┘
```

## Modèle de données

### Table `communes`

Table pivot de référence. Une ligne par commune française (~35 000).

| Colonne           | Type    | Description                        |
|-------------------|---------|------------------------------------|
| code_commune      | VARCHAR | Code INSEE 5 chiffres (PK)        |
| libelle           | VARCHAR | Nom de la commune                  |
| code_departement  | VARCHAR | Code département (2-3 chiffres)    |
| code_region       | VARCHAR | Code région                        |
| population        | INTEGER | Population totale (RP 2021)        |
| superficie        | DOUBLE  | Superficie en km²                  |
| densite           | DOUBLE  | Population / superficie            |
| code_epci         | VARCHAR | Code intercommunalité              |
| libelle_epci      | VARCHAR | Nom de l'intercommunalité          |

Source : RP 2021 (population, superficie) + table EPCI (BANATIC).

### Table `variables_meta`

Registre de toutes les variables disponibles. Alimenté automatiquement depuis `sources.yaml`.

| Colonne     | Type    | Description                                           |
|-------------|---------|-------------------------------------------------------|
| variable_id | VARCHAR | Identifiant unique (PK) — ex: `revenu_median`        |
| source_id   | VARCHAR | Référence à la source dans sources.yaml               |
| name        | VARCHAR | Nom lisible — ex: "Revenu médian par UC"              |
| description | VARCHAR | Description longue                                    |
| category    | VARCHAR | Catégorie thématique (voir liste ci-dessous)          |
| type        | VARCHAR | `numeric`, `categorical`, `flag`                      |
| unit        | VARCHAR | Unité — ex: "€", "%", "pour 1000 hab"                |
| year        | INTEGER | Année de référence de la donnée                       |

**Catégories** :
- `revenus` — revenus, pauvreté, inégalités
- `emploi` — chômage, CSP, activité
- `logement` — propriétaires, HLM, résidences secondaires, loyers, prix immobilier
- `education` — diplômes, IPS, établissements scolaires
- `transport` — gares, stations-service, bornes IRVE, fibre
- `securite` — délinquance
- `sante` — accès aux soins, APL
- `vie_locale` — associations, équipements (BPE)
- `territoire` — densité, DEGURBA, aire d'attraction, QPV, ZRR
- `electoral` — scores par famille politique, abstention

### Table `commune_data` (EAV numérique)

Stockage extensible de toutes les valeurs numériques.

| Colonne       | Type    | Description                    |
|---------------|---------|--------------------------------|
| code_commune  | VARCHAR | FK → communes                  |
| variable_id   | VARCHAR | FK → variables_meta            |
| value         | DOUBLE  | Valeur numérique               |

Index composite sur `(variable_id, code_commune)`.

### Table `commune_data_cat` (EAV catégoriel)

Même structure pour les variables catégorielles (type_territoire, etc.).

| Colonne       | Type    | Description                    |
|---------------|---------|--------------------------------|
| code_commune  | VARCHAR | FK → communes                  |
| variable_id   | VARCHAR | FK → variables_meta            |
| value         | VARCHAR | Valeur catégorielle            |

### Table `elections_raw`

Détail des résultats électoraux par liste et par commune. Conservée pour permettre
des analyses fines au-delà des scores agrégés par famille.

| Colonne              | Type    | Description                        |
|----------------------|---------|------------------------------------|
| code_commune         | VARCHAR | FK → communes                      |
| id_election          | VARCHAR | ex: `2026_muni_t1`, `2022_pres_t1` |
| nuance               | VARCHAR | Code nuance (LDVG, LREP, LRN...)   |
| famille              | VARCHAR | Famille politique (gauche, droite..)|
| libelle_liste        | VARCHAR | Nom de la liste / candidat          |
| inscrits             | INTEGER | Nombre d'inscrits                   |
| votants              | INTEGER | Nombre de votants                   |
| exprimes             | INTEGER | Nombre d'exprimés                   |
| voix                 | INTEGER | Nombre de voix                      |
| pct_voix_exprimes    | DOUBLE  | % voix / exprimés                   |
| pct_voix_inscrits    | DOUBLE  | % voix / inscrits                   |

### Table `geo_communes`

Géométries des communes pour la cartographie.

| Colonne       | Type     | Description                    |
|---------------|----------|--------------------------------|
| code_commune  | VARCHAR  | FK → communes                  |
| geometry      | GEOMETRY | Contour GeoJSON de la commune  |
| centroid_lat  | DOUBLE   | Latitude du centroïde          |
| centroid_lon  | DOUBLE   | Longitude du centroïde         |

### Vue `communes_wide`

Vue matérialisée générée dynamiquement à partir de `variables_meta` + `commune_data`.
Produit une table large avec une colonne par variable, prête pour l'analyse statistique.

```sql
-- Pseudo-code de génération (le vrai code construit le SQL dynamiquement)
CREATE OR REPLACE VIEW communes_wide AS
SELECT
    c.*,
    MAX(CASE WHEN cd.variable_id = 'revenu_median' THEN cd.value END) AS revenu_median,
    MAX(CASE WHEN cd.variable_id = 'taux_pauvrete' THEN cd.value END) AS taux_pauvrete,
    -- ... une colonne par variable dans variables_meta ...
FROM communes c
LEFT JOIN commune_data cd ON c.code_commune = cd.code_commune
GROUP BY c.code_commune;
```

Régénérée automatiquement par `03_load.py` après chaque chargement.

## Registry des sources (`sources.yaml`)

### Structure d'une entrée

```yaml
- id: filosofi_2021
  name: "Revenus et pauvreté (FILOSOFI 2021)"
  category: revenus
  producer: INSEE
  year: 2021

  # Téléchargement
  download:
    type: insee_csv                    # stratégie : datagouv_parquet, insee_csv, insee_xlsx, geojson
    url: "https://www.insee.fr/..."
    filename: "FILO2021_COM.csv"       # nom du fichier dans l'archive si ZIP
    encoding: utf-8
    separator: ";"

  # Jointure
  join_key: CODGEO                     # colonne de jointure vers code_commune

  # Variables extraites
  variables:
    - id: revenu_median
      source_col: MED21
      name: "Revenu médian par UC"
      type: numeric
      unit: "€"
      category: revenus

    - id: taux_pauvrete
      source_col: TP6021
      name: "Taux de pauvreté (seuil 60%)"
      type: numeric
      unit: "%"
      category: revenus

  # Variables calculées (ratios)
  computed:
    - id: pct_imposable
      formula: "PACT21 / 100"          # déjà en % dans la source
      name: "Part des ménages imposés"
      type: numeric
      unit: "%"
      category: revenus
```

### Types de téléchargement

| Type              | Description                                        |
|-------------------|----------------------------------------------------|
| `datagouv_parquet`| Téléchargement direct Parquet via data.gouv        |
| `datagouv_csv`    | Téléchargement direct CSV via data.gouv            |
| `datagouv_api`    | Requête API tabulaire data.gouv (avec pagination)  |
| `insee_csv`       | Téléchargement ZIP INSEE contenant un CSV          |
| `insee_xlsx`      | Téléchargement ZIP INSEE contenant un XLSX         |
| `geojson`         | Téléchargement GeoJSON (contours)                  |
| `custom`          | Logique de téléchargement dans `downloaders/`      |

### Transformers custom

Quand le nettoyage d'une source dépasse le simple mapping de colonnes, on crée un
fichier `pipeline/transformers/<source_id>.py` avec :

```python
import pandas as pd

def transform(df: pd.DataFrame, source_config: dict) -> pd.DataFrame:
    """Nettoyage custom pour cette source.

    Reçoit le DataFrame brut et la config YAML de la source.
    Doit retourner un DataFrame avec code_commune + colonnes nommées
    selon les variable_id du registry.
    """
    # ... nettoyage spécifique ...
    return df
```

Le pipeline détecte automatiquement l'existence du transformer et l'appelle.

## Pipeline — comportement

### Idempotence

Chaque étape peut être relancée sans effet de bord :
- `01_download` : ne re-télécharge pas si le fichier existe déjà (sauf `--force`)
- `02_transform` : régénère les fichiers processed à partir des raw
- `03_load` : fait un DELETE + INSERT par source (pas d'UPSERT incrémental)
- `04_analyze` : recalcule tout à partir de la vue wide

### Orchestration

```bash
# Tout relancer
python pipeline/run.py --all

# Une seule source
python pipeline/run.py --source filosofi_2021

# Seulement une étape
python pipeline/run.py --step download --source filosofi_2021
```

### Gestion des erreurs

- Les téléchargements utilisent un retry exponentiel (3 tentatives)
- Si une source échoue, le pipeline continue avec les autres et reporte l'erreur
- Les fichiers partiellement téléchargés sont supprimés (pas de fichier corrompu)

## Regroupement des nuances politiques

Utilisé pour agréger les résultats électoraux en familles.

```yaml
familles_politiques:
  gauche: [LFI, LDVG, LVEC, LSOC, LUG, LEXG, LCOM, LRDG]
  centre: [LREM, LCNTRE, LMDM, LHORI]
  droite: [LREP, LDVD, LLR, LUD]
  extreme_droite: [LRN, LREC, LEXD]
  sans_etiquette: [LSE, LDIV]
```

Ce mapping est déclaré dans `sources.yaml` (section électorale) et peut être
ajusté sans modifier le code.

## Analyse — découverte automatique des variables

Le module d'analyse ne connaît pas à l'avance la liste des variables.
Il interroge `variables_meta` pour découvrir :

1. **Variables cibles** (catégorie `electoral`) : `score_gauche`, `score_droite`, `pct_abstention`...
2. **Variables explicatives** (toutes les autres catégories numériques)
3. **Variables de segmentation** (catégorielles) : `type_territoire`, flags QPV/ZRR

Cela signifie qu'ajouter une nouvelle variable socio-éco dans le registry la rend
automatiquement disponible dans la matrice de corrélation, l'ACP et la régression.

## Front-end — contrat de données

Le front interroge DuckDB (via duckdb-wasm ou une API légère).

### Endpoints / requêtes type

**Fiche commune** :
```sql
SELECT vm.variable_id, vm.name, vm.category, vm.unit, cd.value
FROM commune_data cd
JOIN variables_meta vm ON cd.variable_id = vm.variable_id
WHERE cd.code_commune = '75056'
ORDER BY vm.category, vm.name;
```

**Comparaison** :
```sql
SELECT cd.code_commune, vm.variable_id, vm.name, cd.value
FROM commune_data cd
JOIN variables_meta vm ON cd.variable_id = vm.variable_id
WHERE cd.code_commune IN ('75056', '13055')
ORDER BY vm.category, vm.name;
```

**Simulateur** (coefficients de régression) :
```sql
SELECT * FROM regression_coefficients;
-- Table pré-calculée par 04_analyze.py
-- Le front applique : score_prédit = Σ(coefficient_i × valeur_curseur_i)
```

**Variables disponibles** (pour construire l'UI dynamiquement) :
```sql
SELECT variable_id, name, category, unit, type
FROM variables_meta
WHERE type = 'numeric'
ORDER BY category, name;
```

## Mises en garde (rappel)

- **Ecological fallacy** : toutes les corrélations sont territoriales, pas individuelles
- **Nuances municipales** : attribuées par les préfectures, peu fiables dans les petites communes
- **Décalage temporel** : données socio-éco de 2021, élections de 2026
- **Communes sans concurrence** : exclure les communes à liste unique de l'analyse politique
