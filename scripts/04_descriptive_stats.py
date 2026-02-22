from pathlib import Path
import pandas as pd

INPUT_PATH = Path("data/processed/edges_features.csv")
OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)

if not INPUT_PATH.exists():
    raise FileNotFoundError(f"Missing input: {INPUT_PATH}")

df = pd.read_csv(INPUT_PATH)

numeric_cols = [
    "montant_count",
    "montant_sum",
    "montant_mean",
    "offresRecues_mean",
    "buyer_degree",
    "supplier_degree",
    "edge_share_buyer",
    "edge_share_supplier",
    "risk_score",
]

existing_cols = [c for c in numeric_cols if c in df.columns]
if not existing_cols:
    raise ValueError("No expected numeric columns found in edges_features.csv")

summary = df[existing_cols].describe(
    percentiles=[0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95]
).T
summary.to_csv(OUT_DIR / "edges_features_summary.csv", index=True)

top_k = df.sort_values("risk_score", ascending=False).head(50)
cols_keep = [
    "acheteur_id",
    "acheteur_nom",
    "titulaire_id",
    "titulaire_nom",
    "montant_count",
    "montant_sum",
    "montant_mean",
    "offresRecues_mean",
    "buyer_degree",
    "supplier_degree",
    "edge_share_buyer",
    "edge_share_supplier",
    "risk_score",
]
cols_keep = [c for c in cols_keep if c in df.columns]
top_k[cols_keep].to_csv(OUT_DIR / "top_risk_edges.csv", index=False)

quantiles = df["risk_score"].quantile([0.0, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 1.0]).to_frame("risk_score")
quantiles.to_csv(OUT_DIR / "risk_score_quantiles.csv")

print(f"edges {len(df)}")
print("summary_cols", ",".join(existing_cols))
print("top_k", len(top_k))
print("risk_score_min", float(df["risk_score"].min()))
print("risk_score_max", float(df["risk_score"].max()))