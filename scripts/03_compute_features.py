import argparse
import os
import numpy as np
import pandas as pd


def minmax(series: pd.Series) -> pd.Series:
    s = series.astype(float)
    vmin = s.min()
    vmax = s.max()
    if pd.isna(vmin) or pd.isna(vmax) or vmax == vmin:
        return pd.Series([0.0] * len(s), index=s.index)
    return (s - vmin) / (vmax - vmin)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute graph features and a baseline risk score")
    parser.add_argument("--input", default="data/interim/edges_agg.csv")
    parser.add_argument("--output", default="data/processed/edges_features.csv")
    args = parser.parse_args()

    df = pd.read_csv(args.input)

    # Ensure numeric fields
    for col in ["montant_sum", "montant_count", "offresRecues_mean"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Buyer/supplier degree (unique partners)
    buyer_degree = df.groupby("acheteur_id")["titulaire_id"].nunique().rename("buyer_degree")
    supplier_degree = df.groupby("titulaire_id")["acheteur_id"].nunique().rename("supplier_degree")
    df = df.merge(buyer_degree, on="acheteur_id", how="left")
    df = df.merge(supplier_degree, on="titulaire_id", how="left")

    # Total amount per buyer/supplier
    buyer_total = df.groupby("acheteur_id")["montant_sum"].sum().rename("buyer_total_amount")
    supplier_total = df.groupby("titulaire_id")["montant_sum"].sum().rename("supplier_total_amount")
    df = df.merge(buyer_total, on="acheteur_id", how="left")
    df = df.merge(supplier_total, on="titulaire_id", how="left")

    # Concentration shares
    df["edge_share_buyer"] = df["montant_sum"] / df["buyer_total_amount"]
    df["edge_share_supplier"] = df["montant_sum"] / df["supplier_total_amount"]

    # Offer-based risk proxy (lower offers => higher risk)
    if "offresRecues_mean" in df.columns:
        offers = df["offresRecues_mean"].copy()
        if offers.isna().any():
            offers = offers.fillna(offers.median())
        df["offers_score"] = 1.0 / (1.0 + offers)
    else:
        df["offers_score"] = 0.0

    # Volume proxies
    df["amount_log"] = np.log1p(df["montant_sum"].fillna(0))
    df["count_score"] = df["montant_count"].fillna(0)

    # Normalize components (0-1)
    df["edge_share_buyer_n"] = minmax(df["edge_share_buyer"].fillna(0))
    df["edge_share_supplier_n"] = minmax(df["edge_share_supplier"].fillna(0))
    df["offers_score_n"] = minmax(df["offers_score"].fillna(0))
    df["amount_log_n"] = minmax(df["amount_log"].fillna(0))
    df["count_score_n"] = minmax(df["count_score"].fillna(0))

    # Baseline risk score (weighted sum)
    df["risk_score"] = (
        0.30 * df["edge_share_buyer_n"]
        + 0.20 * df["edge_share_supplier_n"]
        + 0.20 * df["count_score_n"]
        + 0.20 * df["offers_score_n"]
        + 0.10 * df["amount_log_n"]
    )

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    df.to_csv(args.output, index=False)

    print("edges", len(df))
    print("risk_score_min", float(df["risk_score"].min()))
    print("risk_score_max", float(df["risk_score"].max()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
