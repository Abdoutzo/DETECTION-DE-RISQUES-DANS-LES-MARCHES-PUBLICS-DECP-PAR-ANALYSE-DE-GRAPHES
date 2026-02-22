import argparse
import os
import pandas as pd


def main() -> int:
    parser = argparse.ArgumentParser(description="Build cleaned markets table and aggregated buyer-supplier edges")
    parser.add_argument("--input", default="data/raw/decp_2024H2_travaux_cpv4521_filtered.csv")
    parser.add_argument("--out-markets", default="data/interim/markets_clean.csv")
    parser.add_argument("--out-edges", default="data/interim/edges_agg.csv")
    args = parser.parse_args()

    df = pd.read_csv(args.input)

    # Basic cleaning / typing
    for col in ["acheteur_id", "titulaire_id", "acheteur_nom", "titulaire_nom", "codeCPV", "procedure", "type"]:
        if col in df.columns:
            df[col] = df[col].astype(str)

    if "montant" in df.columns:
        df["montant"] = pd.to_numeric(df["montant"], errors="coerce")
    if "offresRecues" in df.columns:
        df["offresRecues"] = pd.to_numeric(df["offresRecues"], errors="coerce")
    if "dateNotification" in df.columns:
        df["dateNotification"] = pd.to_datetime(df["dateNotification"], errors="coerce")

    # Keep only essential columns for markets
    keep_cols = [
        "uid",
        "id",
        "type",
        "codeCPV",
        "acheteur_id",
        "acheteur_nom",
        "titulaire_id",
        "titulaire_nom",
        "montant",
        "dateNotification",
        "procedure",
        "dureeMois",
        "offresRecues",
        "acheteur_departement_code",
        "titulaire_departement_code",
        "acheteur_region_code",
        "titulaire_region_code",
    ]
    keep_cols = [c for c in keep_cols if c in df.columns]
    markets = df[keep_cols].copy()

    os.makedirs(os.path.dirname(args.out_markets), exist_ok=True)
    markets.to_csv(args.out_markets, index=False)

    # Build aggregated edges
    group_cols = ["acheteur_id", "titulaire_id"]
    agg = {
        "montant": ["count", "sum", "mean", "min", "max"],
        "offresRecues": ["mean", "min", "max"],
        "dateNotification": ["min", "max"],
    }

    edges = markets.groupby(group_cols, dropna=False).agg(agg)
    edges.columns = ["_".join([c for c in col if c]) for col in edges.columns]
    edges = edges.reset_index()

    # Attach names (first seen)
    name_cols = markets[group_cols + ["acheteur_nom", "titulaire_nom"]].drop_duplicates(group_cols)
    edges = edges.merge(name_cols, on=group_cols, how="left")

    # Reorder columns
    front = ["acheteur_id", "acheteur_nom", "titulaire_id", "titulaire_nom"]
    rest = [c for c in edges.columns if c not in front]
    edges = edges[front + rest]

    edges.to_csv(args.out_edges, index=False)

    # Print summary
    print("markets_rows", len(markets))
    print("buyers", markets["acheteur_id"].nunique())
    print("suppliers", markets["titulaire_id"].nunique())
    print("edges", len(edges))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
