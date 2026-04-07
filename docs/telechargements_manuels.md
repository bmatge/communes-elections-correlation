# Téléchargements manuels — Sources INSEE

Les pages INSEE utilisent du JavaScript pour servir les fichiers.
Il faut les télécharger manuellement et les placer dans `data/raw/`.

## État des téléchargements (2026-04-06)

| # | Source | Fichier | Statut | Format obtenu | Format attendu (base IC/CC) |
|---|--------|---------|--------|---------------|----------------------------|
| 1 | FILOSOFI 2021 | `filosofi_2021.csv` | Téléchargé | SDMX long (GEO, FILOSOFI_MEASURE, OBS_VALUE) | Base CC (CODGEO, MED21...) |
| 2 | RP Logement 2021 | `rp_logement_2021.csv` | Téléchargé | TD_LOG1 (CODGEO, CATL, TYPLR, NB) | Base IC (CODGEO, P21_RP...) |
| 3 | RP Activité 2021 | `rp_activite_2021.csv` | Téléchargé | TD_ACT1 (CODGEO, SEXE, AGED65, TACTR_2, NB) | Base IC (CODGEO, P21_CHOM...) |
| 4 | RP Diplômes 2021 | `rp_diplomes_2021.csv` | Téléchargé | Base IRIS (COM, P21_NSCOL15P...) | Base IC (CODGEO, P21_NSCOL15P...) |
| 5 | RP Population 2022 | `rp_population_2022.csv` | Téléchargé | Base IRIS RP 2022 (COM, P22_POP...) | Base IC RP 2021 (CODGEO, P21_POP...) |
| 6 | Grille densité | `grille_densite.csv` | Téléchargé | Converti depuis xlsx (colonnes sales) | CSV propre (CODGEO, DEGURBA) |
| 7 | BPE | `bpe_2021.csv` | Téléchargé | SDMX 2024 (GEO, FACILITY_TYPE, OBS_VALUE) | Base ensemble (DEPCOM, TYPEQU) |
| 8 | RP Mobilité 2021 | `rp_mobilite_2021.csv` | Téléchargé | Flux résidentiels 2022 (CODGEO, DCRAN, NBFLUX) | Base IC couples-familles |
| 9 | Accessibilité services | `accessibilite_services.csv` | **Manquant** | — | CSV (CODGEO, temps d'accès) |

## Conséquences sur les variables

Les formats obtenus diffèrent des bases IC/CC attendues. Des **transformers custom**
sont nécessaires pour reformater chaque fichier. Voir le plan de reformatage.

### Variables disponibles avec transformation
- FILOSOFI : revenu_median, taux_pauvrete, d1, d9, ratio_interdecile + ~15 mesures bonus
- RP Population : population, tranches d'âge, pop étrangère + emploi par secteur (GSEC)
- RP Diplômes : pop 15+ non scolarisée, sans diplôme, CAP-BEP, bac, bac+2/3/4/5+
- RP Activité : chômeurs 15-64, actifs 15-64 → taux de chômage
- RP Logement : résidences principales total, propriétaires, locataires → pct_proprietaires
- Grille densité : DEGURBA (4 catégories)
- BPE : nb d'équipements par domaine (services, enseignement, santé, transport, loisirs, tourisme)
- Mobilité : pct_sedentaire, pct_arrivee_5ans (proxy commune, pas logement)

### Variables perdues (format inadapté)
- **HLM** (rp_hlm, pct_hlm) : TD_LOG1 ne distingue pas HLM / locataire privé
- **Rés. secondaires, logements vacants** : TD_LOG1 ne contient que les résidences principales
- **CS 1-6** (cadres, ouvriers, agriculteurs, employés...) : TD_ACT1 n'a pas les CSP
- **Superficie** : absente des fichiers IRIS (à calculer depuis contours GeoJSON)

### Variable adaptée
- `P21_NSCOL15P_NODIP` attendue → `P21_NSCOL15P_DIPLMIN` obtenue (diplôme minimal = sans diplôme ou CEP, équivalent)

## Instructions de téléchargement (référence)

### 1. FILOSOFI 2021 — Revenus et pauvreté
- **Page** : https://www.insee.fr/fr/statistiques/7756729
- **Fichier obtenu** : format SDMX (DS_FILOSOFI_CC_data.csv dans le ZIP)
- **Idéal** : `FILO2021_DISP_COM.csv` (base CC, une ligne par commune)
- **Placé dans** : `data/raw/filosofi_2021.csv`

### 2. RP 2021 — Logement
- **Page** : https://www.insee.fr/fr/statistiques/7632558
- **Fichier obtenu** : TD_LOG1_2021.csv (tableau détaillé)
- **Idéal** : base IC logement 2021 (base-ic-logement-2021.csv)
- **Placé dans** : `data/raw/rp_logement_2021.csv`

### 3. RP 2021 — Activité des résidents
- **Page** : https://www.insee.fr/fr/statistiques/7632646
- **Fichier obtenu** : TD_ACT1_2021.csv (tableau détaillé)
- **Idéal** : base IC activité résidents 2021 (base-ic-activite-residents-2021.csv)
- **Placé dans** : `data/raw/rp_activite_2021.csv`

### 4. RP 2021 — Diplômes et formation
- **Page** : https://www.insee.fr/fr/statistiques/7632715
- **Fichier obtenu** : base IRIS diplômes formation 2021 — format correct, granularité IRIS
- **Colonnes** : COM, P21_NSCOL15P, P21_NSCOL15P_DIPLMIN, _BEPC, _CAPBEP, _BAC, _SUP2, _SUP34, _SUP5
- **Placé dans** : `data/raw/rp_diplomes_2021.csv`

### 5. RP 2022 — Évolution et structure de la population
- **Page** : https://www.insee.fr/fr/statistiques/7631458
- **Fichier obtenu** : base IRIS RP 2022 (pas 2021), avec colonnes P22_POP, P22_POP_ETR, C22_POP15P_STAT_GSEC*
- **Note** : SUPERF absent, GSEC = secteurs d'activité (pas CSP)
- **Placé dans** : `data/raw/rp_population_2022.csv`

### 6. Grille de densité communale
- **Page** : https://www.insee.fr/fr/information/2114627
- **Fichier obtenu** : grille_densite_2021_agrege.xlsx, converti en CSV
- **Note** : colonnes avec retours à la ligne à nettoyer
- **Placé dans** : `data/raw/grille_densite.csv`

### 7. BPE — Base permanente des équipements
- **Page** : https://www.insee.fr/fr/statistiques/8217537
- **Fichier obtenu** : DS_BPE_2024_data.csv (format SDMX, données 2024)
- **Idéal** : bpe21_ensemble_xy.csv (un enregistrement par équipement)
- **Placé dans** : `data/raw/bpe_2021.csv`

### 8. RP 2022 — Mobilités résidentielles (couche 3)
- **Page** : https://www.insee.fr/fr/statistiques/7632715
- **Fichier obtenu** : base-flux-mobilite-residentielle-2022.csv (flux entre communes)
- **Note** : proxy "même commune" et non "même logement"
- **Placé dans** : `data/raw/rp_mobilite_2021.csv`

### 9. Accessibilité aux services (couche 3)
- **Page** : https://www.insee.fr/fr/statistiques/3568812
- **Fichier** : indicateurs d'accès aux services, format CSV
- **Renommer en** : `data/raw/accessibilite_services.csv`
- **Statut** : **NON TÉLÉCHARGÉ**

## Après téléchargement

```bash
# Vérifier que les fichiers sont bien là
ls -lh data/raw/filosofi_2021.csv data/raw/rp_*.csv data/raw/grille_densite.csv data/raw/bpe_2021.csv

# Lancer le pipeline (les transformers custom gèrent le reformatage)
python -m pipeline.transform -s filosofi_2021 rp_logement_2021 rp_activite_2021 rp_diplomes_2021 rp_population_2022 grille_densite bpe_2021 rp_mobilite_2021 -f
```
