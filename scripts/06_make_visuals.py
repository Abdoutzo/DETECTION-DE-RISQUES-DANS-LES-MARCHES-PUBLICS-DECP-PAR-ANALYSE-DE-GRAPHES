from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx

FIG_DIR = Path('reports/figures')
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    'figure.dpi': 130,
    'savefig.dpi': 130,
    'font.size': 10,
})

# Step 1: Data collection visuals
raw_path = Path('data/raw/decp_2024H2_travaux_cpv4521_filtered.csv')
raw = pd.read_csv(raw_path)
raw['dateNotification'] = pd.to_datetime(raw['dateNotification'], errors='coerce')
raw['month'] = raw['dateNotification'].dt.to_period('M').astype(str)
month_counts = raw['month'].value_counts().sort_index()

fig, ax = plt.subplots(figsize=(6.5, 3.5))
ax.bar(month_counts.index, month_counts.values, color='#4C78A8')
ax.set_title('Step 1 - Contracts per month (H2 2024)')
ax.set_xlabel('Month')
ax.set_ylabel('Number of contracts')
ax.tick_params(axis='x', rotation=45)
fig.tight_layout()
fig.savefig(FIG_DIR / 'step1_monthly_counts.png')
plt.close(fig)

# Step 2: Graph construction visuals
edges_path = Path('data/interim/edges_agg.csv')
edges = pd.read_csv(edges_path)

buyer_deg = edges.groupby('acheteur_id').size()
supplier_deg = edges.groupby('titulaire_id').size()

fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.5), sharey=True)
axes[0].hist(buyer_deg.values, bins=20, color='#59A14F')
axes[0].set_title('Buyer degree distribution')
axes[0].set_xlabel('Degree')
axes[0].set_ylabel('Count of buyers')

axes[1].hist(supplier_deg.values, bins=20, color='#F28E2B')
axes[1].set_title('Supplier degree distribution')
axes[1].set_xlabel('Degree')

fig.suptitle('Step 2 - Degree distributions (buyers / suppliers)', y=1.02)
fig.tight_layout()
fig.savefig(FIG_DIR / 'step2_degree_distributions.png')
plt.close(fig)

# Step 3: Feature engineering visuals
feat_path = Path('data/processed/edges_features.csv')
feat = pd.read_csv(feat_path)

fig, ax = plt.subplots(figsize=(6.5, 3.5))
ax.hist(feat['edge_share_buyer'].dropna(), bins=25, alpha=0.7, label='Edge share (buyer)', color='#4C78A8')
ax.hist(feat['edge_share_supplier'].dropna(), bins=25, alpha=0.7, label='Edge share (supplier)', color='#F28E2B')
ax.set_title('Step 3 - Edge share distributions')
ax.set_xlabel('Edge share')
ax.set_ylabel('Edges')
ax.legend()
fig.tight_layout()
fig.savefig(FIG_DIR / 'step3_edge_share.png')
plt.close(fig)

# Step 4: Descriptive analysis visuals
fig, ax = plt.subplots(figsize=(6.5, 3.5))
ax.hist(feat['risk_score'].dropna(), bins=30, color='#9C755F')
q90 = feat['risk_score'].quantile(0.90)
q95 = feat['risk_score'].quantile(0.95)
q99 = feat['risk_score'].quantile(0.99)
for q, label, color in [(q90, 'p90', '#4C78A8'), (q95, 'p95', '#F28E2B'), (q99, 'p99', '#E15759')]:
    ax.axvline(q, linestyle='--', color=color, linewidth=1, label=label)
ax.set_title('Step 4 - Risk score distribution')
ax.set_xlabel('Risk score')
ax.set_ylabel('Edges')
ax.legend()
fig.tight_layout()
fig.savefig(FIG_DIR / 'step4_risk_score_dist.png')
plt.close(fig)

# Step 5: Risk score analysis visuals
feat['high95'] = feat['risk_score'] >= q95
high = feat.loc[feat['high95'], 'offresRecues_mean']
low = feat.loc[~feat['high95'], 'offresRecues_mean']

fig, ax = plt.subplots(figsize=(6.0, 3.5))
ax.boxplot([low.dropna(), high.dropna()], tick_labels=['< p95', '>= p95'], patch_artist=True,
           boxprops=dict(facecolor='#59A14F', alpha=0.7),
           medianprops=dict(color='black'))
ax.set_title('Step 5 - Offers received (low vs high risk)')
ax.set_ylabel('Mean offers received')
fig.tight_layout()
fig.savefig(FIG_DIR / 'step5_offers_low_vs_high.png')
plt.close(fig)

# Step 6: Case studies visuals
case = feat.sort_values('risk_score', ascending=False).head(20).copy()
case['rank'] = range(1, len(case) + 1)

fig, ax = plt.subplots(figsize=(7.0, 3.5))
ax.bar(case['rank'], case['risk_score'], color='#E15759')
ax.set_title('Step 6 - Top 20 risk scores (anonymized)')
ax.set_xlabel('Rank')
ax.set_ylabel('Risk score')
fig.tight_layout()
fig.savefig(FIG_DIR / 'step6_top20_risk.png')
plt.close(fig)

# Step 7: Evaluation visual (risk vs offers)
fig, ax = plt.subplots(figsize=(6.5, 3.5))
ax.scatter(
    feat['offresRecues_mean'],
    feat['risk_score'],
    s=10,
    alpha=0.4,
    color='#4C78A8'
)
ax.set_title('Step 7 - Risk score vs offers received')
ax.set_xlabel('Mean offers received')
ax.set_ylabel('Risk score')
fig.tight_layout()
fig.savefig(FIG_DIR / 'step7_risk_vs_offers.png')
plt.close(fig)

# Step 8: Centrality on supplier projection (PageRank)
buyers = edges['acheteur_id'].astype(str)
suppliers = edges['titulaire_id'].astype(str)

B = nx.Graph()
B.add_nodes_from(buyers.unique(), bipartite='buyer')
B.add_nodes_from(suppliers.unique(), bipartite='supplier')
B.add_edges_from(zip(buyers, suppliers))

supplier_nodes = set(suppliers.unique())
proj = nx.bipartite.weighted_projected_graph(B, supplier_nodes)
pr = nx.pagerank(proj, weight='weight')
pr_series = pd.Series(pr, name='pagerank').sort_values(ascending=False)
top10 = pr_series.head(10).reset_index()
top10.columns = ['supplier_id', 'pagerank']

top10_path = Path('data/processed/suppliers_pagerank_top10.csv')
top10_path.parent.mkdir(parents=True, exist_ok=True)
top10.to_csv(top10_path, index=False)

fig, ax = plt.subplots(figsize=(6.5, 3.2))
ax.barh(top10['supplier_id'].astype(str), top10['pagerank'], color='#4C78A8')
ax.invert_yaxis()
ax.set_title('Step 8 - Top 10 suppliers by PageRank (projection)')
ax.set_xlabel('PageRank')
ax.set_ylabel('Supplier (SIRET)')
fig.tight_layout()
fig.savefig(FIG_DIR / 'step8_pagerank_suppliers.png')
plt.close(fig)

print('Figures saved to', FIG_DIR)
