import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd


def build_supplier_projection(df: pd.DataFrame) -> nx.Graph:
    buyers = "b::" + df["acheteur_id"].astype(str)
    suppliers = "s::" + df["titulaire_id"].astype(str)

    b = nx.Graph()
    b.add_nodes_from(buyers.unique(), bipartite="buyer")
    b.add_nodes_from(suppliers.unique(), bipartite="supplier")
    b.add_edges_from(zip(buyers, suppliers))

    supplier_nodes = list(suppliers.unique())
    proj = nx.bipartite.weighted_projected_graph(b, supplier_nodes)
    return proj


def detect_louvain_communities(
    proj: nx.Graph, resolution: float, seed: int
) -> tuple[list[set[str]], float]:
    communities = nx.community.louvain_communities(
        proj,
        weight="weight",
        resolution=resolution,
        seed=seed,
    )
    modularity = nx.community.modularity(proj, communities, weight="weight")
    return communities, float(modularity)


def save_community_figure(
    summary: pd.DataFrame,
    out_path: Path,
    global_high_risk_share: float,
    min_community_edges: int,
    top_k: int,
) -> None:
    plot_df = summary[summary["edges_count"] >= min_community_edges].copy()
    if plot_df.empty:
        # Fallback if all communities are tiny.
        plot_df = summary.copy()

    top = (
        plot_df.sort_values(["high_risk_share", "edges_count"], ascending=[False, False])
        .head(top_k)
        .sort_values("high_risk_share", ascending=True)
    )

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))

    # Panel A: communities with highest share of high-risk edges.
    labels = [f"C{int(c)} (n={int(n)})" for c, n in zip(top["community_id"], top["edges_count"])]
    axes[0].barh(labels, top["high_risk_share"] * 100, color="#4C78A8")
    axes[0].axvline(global_high_risk_share * 100, color="#E15759", linestyle="--", linewidth=1.5)
    axes[0].set_title("Top communities by high-risk edge share")
    axes[0].set_xlabel("High-risk edges (%)")
    axes[0].set_ylabel("Community")

    # Panel B: size-risk map for all communities.
    sizes = np.clip(summary["suppliers_count"].astype(float) * 9.0, 30.0, 450.0)
    scatter = axes[1].scatter(
        summary["edges_count"],
        summary["high_risk_share"] * 100,
        s=sizes,
        c=summary["mean_risk"],
        cmap="viridis",
        alpha=0.75,
        edgecolor="black",
        linewidth=0.2,
    )
    axes[1].axhline(global_high_risk_share * 100, color="#E15759", linestyle="--", linewidth=1.5)
    axes[1].set_title("Community size vs high-risk share")
    axes[1].set_xlabel("Edges in community")
    axes[1].set_ylabel("High-risk edges (%)")
    cbar = fig.colorbar(scatter, ax=axes[1])
    cbar.set_label("Mean risk score")

    fig.suptitle("Step 9 - Community detection (Louvain) and modularity analysis", y=1.02)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run supplier-community analysis with Louvain + modularity"
    )
    parser.add_argument("--input", default="data/processed/edges_features.csv")
    parser.add_argument(
        "--out-supplier-communities",
        default="data/processed/supplier_communities.csv",
    )
    parser.add_argument(
        "--out-community-summary",
        default="data/processed/community_risk_summary.csv",
    )
    parser.add_argument(
        "--out-metrics",
        default="data/processed/community_modularity_metrics.csv",
    )
    parser.add_argument(
        "--out-top-large",
        default="data/processed/community_risk_top_large.csv",
    )
    parser.add_argument(
        "--out-figure",
        default="reports/figures/step9_community_modularity.png",
    )
    parser.add_argument("--resolution", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--runs", type=int, default=12)
    parser.add_argument("--top-k", type=int, default=12)
    parser.add_argument("--min-community-edges", type=int, default=20)
    args = parser.parse_args()

    df = pd.read_csv(args.input)

    required = {"acheteur_id", "titulaire_id", "risk_score"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    # Build supplier projection and detect communities.
    proj = build_supplier_projection(df)
    runs: list[dict] = []
    for i in range(args.runs):
        run_seed = args.seed + i
        run_communities, run_modularity = detect_louvain_communities(
            proj,
            resolution=args.resolution,
            seed=run_seed,
        )
        runs.append(
            {
                "seed": run_seed,
                "communities": run_communities,
                "modularity": run_modularity,
                "communities_count": len(run_communities),
            }
        )

    # Keep the partition with the best modularity (tie-breaker: lower seed).
    runs_sorted = sorted(runs, key=lambda x: (-x["modularity"], x["seed"]))
    best = runs_sorted[0]
    communities = best["communities"]
    modularity = float(best["modularity"])
    best_seed = int(best["seed"])

    modularity_values = [float(r["modularity"]) for r in runs]

    # Supplier-level community assignment.
    supplier_to_comm: dict[str, int] = {}
    for cid, community in enumerate(communities):
        for s_prefixed in community:
            supplier_to_comm[s_prefixed.replace("s::", "", 1)] = cid

    supplier_df = pd.DataFrame(
        {
            "titulaire_id": list(supplier_to_comm.keys()),
            "community_id": list(supplier_to_comm.values()),
        }
    )
    community_sizes = supplier_df["community_id"].value_counts().rename("community_size")
    supplier_df = supplier_df.merge(
        community_sizes,
        left_on="community_id",
        right_index=True,
        how="left",
    )

    weighted_degree = dict(proj.degree(weight="weight"))
    degree = dict(proj.degree())
    supplier_df["supplier_degree_proj"] = supplier_df["titulaire_id"].map(
        lambda x: degree.get(f"s::{x}", 0)
    )
    supplier_df["supplier_wdegree_proj"] = supplier_df["titulaire_id"].map(
        lambda x: weighted_degree.get(f"s::{x}", 0.0)
    )

    # Edge-level aggregation by supplier community.
    df["titulaire_id"] = df["titulaire_id"].astype(str)
    df["acheteur_id"] = df["acheteur_id"].astype(str)
    edges = df.merge(supplier_df[["titulaire_id", "community_id"]], on="titulaire_id", how="left")

    p95 = float(edges["risk_score"].quantile(0.95))
    edges["high_risk"] = edges["risk_score"] >= p95
    global_high_risk_share = float(edges["high_risk"].mean())

    summary = (
        edges.groupby("community_id")
        .agg(
            suppliers_count=("titulaire_id", "nunique"),
            buyers_count=("acheteur_id", "nunique"),
            edges_count=("risk_score", "size"),
            high_risk_edges=("high_risk", "sum"),
            mean_risk=("risk_score", "mean"),
            median_risk=("risk_score", "median"),
            mean_offers=("offresRecues_mean", "mean"),
            mean_edge_share_buyer=("edge_share_buyer", "mean"),
            mean_edge_share_supplier=("edge_share_supplier", "mean"),
        )
        .reset_index()
    )
    summary["high_risk_share"] = summary["high_risk_edges"] / summary["edges_count"]
    summary["high_risk_enrichment"] = summary["high_risk_share"] / global_high_risk_share
    summary = summary.sort_values(
        ["high_risk_share", "high_risk_edges", "edges_count"],
        ascending=[False, False, False],
    )
    top_large = (
        summary[summary["edges_count"] >= args.min_community_edges]
        .sort_values(["high_risk_share", "high_risk_edges", "edges_count"], ascending=[False, False, False])
        .head(args.top_k)
        .copy()
    )

    # One-row metrics table for direct citation in the report.
    metrics = pd.DataFrame(
        [
            {
                "projection_nodes": proj.number_of_nodes(),
                "projection_edges": proj.number_of_edges(),
                "communities_count": len(communities),
                "largest_community_suppliers": int(community_sizes.max()),
                "modularity": modularity,
                "louvain_runs": int(args.runs),
                "seed_start": int(args.seed),
                "best_seed": best_seed,
                "modularity_mean": float(np.mean(modularity_values)),
                "modularity_std": float(np.std(modularity_values)),
                "modularity_min": float(np.min(modularity_values)),
                "modularity_max": float(np.max(modularity_values)),
                "risk_p95_threshold": p95,
                "global_high_risk_share": global_high_risk_share,
            }
        ]
    )

    out_supplier = Path(args.out_supplier_communities)
    out_summary = Path(args.out_community_summary)
    out_metrics = Path(args.out_metrics)
    out_top_large = Path(args.out_top_large)
    out_supplier.parent.mkdir(parents=True, exist_ok=True)
    out_summary.parent.mkdir(parents=True, exist_ok=True)
    out_metrics.parent.mkdir(parents=True, exist_ok=True)
    out_top_large.parent.mkdir(parents=True, exist_ok=True)
    supplier_df.to_csv(out_supplier, index=False)
    summary.to_csv(out_summary, index=False)
    metrics.to_csv(out_metrics, index=False)
    top_large.to_csv(out_top_large, index=False)

    save_community_figure(
        summary=summary,
        out_path=Path(args.out_figure),
        global_high_risk_share=global_high_risk_share,
        min_community_edges=args.min_community_edges,
        top_k=args.top_k,
    )

    print("projection_nodes", proj.number_of_nodes())
    print("projection_edges", proj.number_of_edges())
    print("communities_count", len(communities))
    print("modularity_best", round(modularity, 6))
    print("best_seed", best_seed)
    print("modularity_mean", round(float(np.mean(modularity_values)), 6))
    print("modularity_std", round(float(np.std(modularity_values)), 6))
    print("global_high_risk_share", round(global_high_risk_share, 6))
    print("largest_community_suppliers", int(community_sizes.max()))
    print("saved_supplier_communities", args.out_supplier_communities)
    print("saved_community_summary", args.out_community_summary)
    print("saved_metrics", args.out_metrics)
    print("saved_top_large", args.out_top_large)
    print("saved_figure", args.out_figure)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
