from pathlib import Path
import pandas as pd

INPUT_PATH = Path('data/processed/edges_features.csv')
OUT_DIR = Path('data/processed')
OUT_DIR.mkdir(parents=True, exist_ok=True)

if not INPUT_PATH.exists():
    raise FileNotFoundError(f"Missing input: {INPUT_PATH}")

# Load features
edges = pd.read_csv(INPUT_PATH)

# Top 20 edges by risk score (case studies)
case_cols = [
    'acheteur_id','acheteur_nom','titulaire_id','titulaire_nom',
    'montant_count','montant_sum','montant_mean',
    'offresRecues_mean','buyer_degree','supplier_degree',
    'edge_share_buyer','edge_share_supplier','risk_score',
    'dateNotification_min','dateNotification_max'
]
case_cols = [c for c in case_cols if c in edges.columns]

top20 = edges.sort_values('risk_score', ascending=False).head(20)
top20[case_cols].to_csv(OUT_DIR / 'case_studies_top20.csv', index=False)

# Buyers with multiple high-risk edges (>=95th percentile)
q95 = edges['risk_score'].quantile(0.95)
edges['high95'] = edges['risk_score'] >= q95
buyers_hr = (
    edges.groupby('acheteur_id')
    .agg(high_edges=('high95','sum'), edges=('risk_score','size'), max_risk=('risk_score','max'))
    .sort_values(['high_edges','max_risk','edges'], ascending=False)
)

buyers_hr.head(20).to_csv(OUT_DIR / 'buyers_high_risk.csv')

suppliers_hr = (
    edges.groupby('titulaire_id')
    .agg(high_edges=('high95','sum'), edges=('risk_score','size'), max_risk=('risk_score','max'))
    .sort_values(['high_edges','max_risk','edges'], ascending=False)
)

suppliers_hr.head(20).to_csv(OUT_DIR / 'suppliers_high_risk.csv')

print('top20', len(top20))
print('buyers_high_risk', buyers_hr.head(20).shape[0])
print('suppliers_high_risk', suppliers_hr.head(20).shape[0])