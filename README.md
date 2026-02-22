# Detection de risques dans les marches publics (DECP) par analyse de graphes

Projet de cours "Graph Analytics and Applications" (Ecole Centrale Casablanca).

## Objectif
Construire un score de risque interpretable sur des relations acheteur-fournisseur
dans les marches publics DECP, puis analyser ces relations par:
- ranking d'aretes acheteur-fournisseur,
- indicateurs de centralite,
- analyse de communautes (Louvain + modularite).

## Contenu du depot (version prof)
- `scripts/`: pipeline complet (`01` a `07`)
- `configs/`: configurations de collecte DECP
- `reports/iclr_report/`: rapport final LaTeX (template ICLR)
- `reports/figures/`: figures finales (steps 1 a 9)
- `data/processed/`: sorties finales compactes pour lecture/resultats
- `requirements.txt`: dependances Python

Les fichiers de cours, PDF annexes et donnees brutes/intermediaires ne sont pas commites.

## Reproduction rapide
Prerequis: Python 3.10+.

```bash
pip install -r requirements.txt
python scripts/01_collect_decp.py --config configs/collect_decp_2024H2_travaux_4521_filtered.json
python scripts/02_build_edges.py
python scripts/03_compute_features.py
python scripts/04_descriptive_stats.py
python scripts/05_case_studies.py
python scripts/06_make_visuals.py
python scripts/07_community_modularity.py
```

## Resultats principaux a consulter
- Rapport: `reports/iclr_report/main.tex`
- Figures:
  - `reports/figures/step4_risk_score_dist.png`
  - `reports/figures/step5_offers_low_vs_high.png`
  - `reports/figures/step7_risk_vs_offers.png`
  - `reports/figures/step8_pagerank_suppliers.png`
  - `reports/figures/step9_community_modularity.png`
- Tableaux CSV:
  - `data/processed/top_risk_edges.csv`
  - `data/processed/risk_score_quantiles.csv`
  - `data/processed/community_modularity_metrics.csv`
  - `data/processed/community_risk_top_large.csv`

## Interpretation courte
Le score de risque est un outil de priorisation, pas une preuve de fraude.
L'analyse communautaire ajoute une lecture structurelle: le reseau est fortement
structure en communautes, mais le risque reste surtout relationnel (niveau arete).
