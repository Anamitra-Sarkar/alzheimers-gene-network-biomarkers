"""
Real end-to-end run: STRING PPI -> protein->gene-symbol translation -> RWR from AD
seed genes -> topology features -> leave-one-seed-out fusion evaluation vs degree
baseline. Wires together the already-implemented building blocks
(string_parser, string_info, rwr, features, fusion, seed_genes) which previously had
no single orchestrating entry point for a real run.

Usage (Kaggle/Modal):
  python -m data_pipeline.real_run \
    --string-path data/raw/9606.protein.links.v12.0.txt.gz \
    --string-info-path data/raw/9606.protein.info.v12.0.txt.gz \
    --out artifacts/real-run-1
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from data_pipeline.string_parser import parse_string_links, build_adjacency, column_normalize
from data_pipeline.string_info import parse_string_info, translate_gene_list
from data_pipeline.seed_genes import SEED_GENES, get_seed_vector, get_seed_genes_present
from data_pipeline.rwr import random_walk_with_restart
from data_pipeline.features import compute_features
from data_pipeline.fusion import build_model, evaluate_ranking


def _leave_one_seed_out_eval_no_leakage(adj, W, gene_list, features_df, labels, seeds_present,
                                          feature_cols, model_type: str = "logistic"):
    """
    Leave-one-seed-out CV where the RWR score feature is recomputed PER FOLD with the
    held-out seed gene excluded from the RWR seed set -- avoids the leakage of a
    globally-seeded rwr_score encoding "this gene was a seed" into its own held-out
    evaluation. degree/pagerank/betweenness/closeness are topology-only and reused
    as-is (not a function of the seed set, safe).
    """
    n = len(labels)
    pos_idx = np.where(labels == 1)[0]
    neg_idx = np.where(labels == 0)[0]
    rwr_col = feature_cols.index("rwr_score") if "rwr_score" in feature_cols else None
    X_base = features_df[feature_cols].values.astype(float)

    oof_scores = np.zeros(n, dtype=float)
    neg_scores_accum = np.zeros(len(neg_idx))

    seeds_upper = set(s.upper() for s in seeds_present)
    gene_list_upper = [g.upper() for g in gene_list]

    for p in pos_idx:
        held_out_symbol = gene_list_upper[p]
        fold_seed_genes = [s for s in seeds_present if s.upper() != held_out_symbol]

        X = X_base.copy()
        if rwr_col is not None:
            p0_fold = get_seed_vector(gene_list, fold_seed_genes)
            rwr_fold = random_walk_with_restart(W, p0_fold, restart_prob=0.3, tol=1e-6)
            X[:, rwr_col] = rwr_fold

        train_mask = np.ones(n, dtype=bool)
        train_mask[p] = False
        model = build_model(model_type)
        model.fit(X[train_mask], labels[train_mask])
        oof_scores[p] = model.predict_proba(X[p : p + 1])[0, 1]
        neg_scores_accum += model.predict_proba(X[neg_idx])[:, 1]

    if len(pos_idx) > 0:
        neg_scores_accum /= len(pos_idx)
        oof_scores[neg_idx] = neg_scores_accum

    baseline = features_df["degree_norm"].values
    return evaluate_ranking(labels, oof_scores, baseline, ks=[10, 25, 50, 100])


def run(string_path: str, string_info_path: str, out_dir: str, threshold: int = 700,
        model_type: str = "logistic", betweenness_k: int = 200) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"[1/5] Parsing STRING links (threshold={threshold})...")
    proteins, edges = parse_string_links(string_path, confidence_threshold=threshold)
    print(f"  {len(proteins)} proteins, {len(edges)} edges")

    print("[2/5] Translating STRING protein IDs -> gene symbols via protein.info...")
    id_to_symbol = parse_string_info(string_info_path)
    gene_list = translate_gene_list(proteins, id_to_symbol)
    n_translated = sum(1 for g in gene_list if g in id_to_symbol.values())
    print(f"  {n_translated}/{len(gene_list)} proteins translated to gene symbols")

    seeds_present = get_seed_genes_present(gene_list, SEED_GENES)
    print(f"  AD seed genes present in graph: {len(seeds_present)}/{len(SEED_GENES)}: {seeds_present}")
    if len(seeds_present) < 5:
        raise RuntimeError(
            f"Only {len(seeds_present)} seed genes found in the real graph after translation -- "
            "something is wrong with the protein->symbol mapping, aborting rather than "
            "reporting a meaningless evaluation."
        )

    print("[3/5] Building adjacency + running RWR from seed genes...")
    adj = build_adjacency(len(proteins), edges, weighted=False)
    W = column_normalize(adj)
    p0 = get_seed_vector(gene_list, SEED_GENES)
    rwr_scores = random_walk_with_restart(W, p0, restart_prob=0.3, tol=1e-6)

    print(f"[4/5] Computing topology features (betweenness_k={betweenness_k} approx sampling)...")
    # NOTE: degree/pagerank/betweenness/closeness are graph-topology-only (not a function
    # of the seed set) and are safe to compute once. rwr_score IS a function of the seed
    # set and is recomputed per-fold below with the held-out gene excluded from seeding --
    # using the globally-seeded rwr_score directly in leave-one-seed-out CV would leak
    # "this gene was a seed" information into its own held-out evaluation (a real bug
    # caught on the first run of this pipeline: it produced a suspicious AUPRC of ~1.0).
    features_df = compute_features(adj, gene_list, rwr_scores=rwr_scores, betweenness_k=betweenness_k)

    labels = np.array([1 if g in set(s.upper() for s in seeds_present) else 0
                        for g in [x.upper() for x in gene_list]], dtype=int)
    print(f"  {labels.sum()} positive (seed) genes, {len(labels) - labels.sum()} negative")

    feature_cols = ["degree_norm", "pagerank", "betweenness", "closeness", "rwr_score"]
    feature_cols = [c for c in feature_cols if c in features_df.columns]

    print("[5/5] Running LEAKAGE-FREE leave-one-seed-out CV (fusion vs degree-only baseline)...")
    result = _leave_one_seed_out_eval_no_leakage(
        adj, W, gene_list, features_df, labels, seeds_present, feature_cols, model_type=model_type
    )

    summary = {
        "n_genes": len(gene_list),
        "n_edges": len(edges),
        "threshold": threshold,
        "n_seed_genes_present": len(seeds_present),
        "seed_genes_present": seeds_present,
        "model_type": model_type,
        "feature_cols": feature_cols,
        "fusion": {"recall_at_k": result.recall_at_k, "auprc": result.auprc},
        "degree_baseline": {"recall_at_k": result.baseline_recall_at_k, "auprc": result.baseline_auprc},
        "interpretation": (
            "fusion beats degree-only baseline" if result.auprc > result.baseline_auprc
            else "fusion does NOT beat degree-only baseline (honest)"
        ),
    }
    with open(out / "metrics.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps({"fusion_auprc": result.auprc, "degree_baseline_auprc": result.baseline_auprc}, indent=2))
    print(f"Interpretation: {summary['interpretation']}")
    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--string-path", required=True)
    p.add_argument("--string-info-path", required=True)
    p.add_argument("--out", default="artifacts/real-run-1")
    p.add_argument("--threshold", type=int, default=700)
    p.add_argument("--model-type", choices=["logistic", "gbt"], default="logistic")
    p.add_argument("--betweenness-k", type=int, default=200)
    args = p.parse_args()
    run(args.string_path, args.string_info_path, args.out, args.threshold, args.model_type, args.betweenness_k)


if __name__ == "__main__":
    main()
