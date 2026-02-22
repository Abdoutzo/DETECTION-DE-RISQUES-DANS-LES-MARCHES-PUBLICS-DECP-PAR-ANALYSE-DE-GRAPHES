# Detection de risques dans les marches publics (DECP) par analyse de graphes

## Contexte
Ce depot contient le code et les sorties d'une etude
de priorisation de risque sur les marches publics DECP.

Probleme traite:
- modeliser les attributions acheteur-fournisseur sous forme de graphe,
- construire un score de risque interpretable au niveau relation (arete),
- produire un classement exploitable pour la priorisation des controles,
- completer l'analyse par centralite (PageRank) et communautes (Louvain + modularite).

## Perimetre des donnees
Filtrage applique (config principale):
- periode: 2024-07-01 a 2025-01-01 (H2 2024),
- type: Travaux,
- domaine: CPV contenant `4521`,
- borne montant: 5 000 a 20 000 000,
- identifiant titulaire: SIRET.

## Pipeline code (scripts)
Le pipeline est decoupe en scripts numerotes:

1. `scripts/01_collect_decp.py`
   collecte DECP via API tabulaire (`configs/*.json`).
2. `scripts/02_build_edges.py`
   nettoyage minimal + construction du graphe biparti + agregation des aretes.
3. `scripts/03_compute_features.py`
   calcul des features de graphe et du score de risque baseline.
4. `scripts/04_descriptive_stats.py`
   statistiques descriptives, quantiles et top relations a risque.
5. `scripts/05_case_studies.py`
   extraction des cas prioritaires (top20, acheteurs/fournisseurs a risque).
6. `scripts/06_make_visuals.py`
   generation des figures principales (steps 1 a 8).
7. `scripts/07_community_modularity.py`
   projection fournisseurs, Louvain multi-runs, modularite, analyse communautaire,
   export de la figure `step9_community_modularity.png`.

## Structure du depot
- `configs/` : configurations de collecte API.
- `scripts/` : pipeline complet de preparation, scoring et visualisation.
- `reports/figures/` : figures finales generees par le pipeline.
- `data/processed/` : sorties compactes utiles a l'evaluation (CSV de resultats).
- `requirements.txt` : dependances Python.

## Execution
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

## Resultats a consulter en priorite
Figures:
- `reports/figures/step4_risk_score_dist.png`
- `reports/figures/step5_offers_low_vs_high.png`
- `reports/figures/step7_risk_vs_offers.png`
- `reports/figures/step8_pagerank_suppliers.png`
- `reports/figures/step9_community_modularity.png`

Tableaux:
- `data/processed/top_risk_edges.csv`
- `data/processed/risk_score_quantiles.csv`
- `data/processed/edges_features_summary.csv`
- `data/processed/community_modularity_metrics.csv`
- `data/processed/community_risk_top_large.csv`

## Lecture rapide des contributions
- score interpretable pour ranking des relations acheteur-fournisseur,
- verification descriptive des signaux de risque (concentration, concurrence),
- centralite structurelle (PageRank sur projection fournisseurs),
- analyse communautaire avec modularite elevee et lecture de la concentration du risque.

## Politique de versionnement
Le depot versionne uniquement les elements necessaires a l'evaluation et a la
reproduction. Les fichiers de cours, annexes PDF, donnees brutes et intermediaires
ne sont pas inclus.
