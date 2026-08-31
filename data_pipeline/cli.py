"""
CLI entry points for real runs (Kaggle/Modal).
e.g.:
  python -m data_pipeline.cli build-graph --string-path /data/9606.protein.links.v12.0.txt.gz --output /data/graph.npz --threshold 700
  python -m data_pipeline.cli run-rwr --graph /data/graph.npz --output /data/rwr.npy
  python -m data_pipeline.cli train --features /data/features.parquet --output /data/model.joblib
"""

from __future__ import annotations

import argparse
import pathlib
import pickle

import numpy as np
import scipy.sparse as sp

from data_pipeline.string_parser import parse_string_links, build_adjacency, column_normalize
from data_pipeline.seed_genes import SEED_GENES, get_seed_vector
from data_pipeline.rwr import random_walk_with_restart
from data_pipeline.features import compute_features
from data_pipeline.fusion import train_fusion_model


def cmd_build_graph(args: argparse.Namespace) -> None:
    print(f"Parsing STRING file: {args.string_path} (threshold={args.threshold})")
    proteins, edges = parse_string_links(args.string_path, confidence_threshold=args.threshold)
    print(f"  Proteins: {len(proteins)}, edges: {len(edges)}")
    adj = build_adjacency(len(proteins), edges, weighted=args.weighted)
    print(f"  Adjacency: {adj.shape}, nnz={adj.nnz}")
    out = pathlib.Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    sp.save_npz(str(out.with_suffix(".npz")), adj)
    # save protein list
    with open(out.with_suffix(".proteins.txt"), "w") as f:
        for p in proteins:
            f.write(p + "\n")
    print(f"Saved to {out.with_suffix('.npz')}")


def cmd_run_rwr(args: argparse.Namespace) -> None:
    if not 0 < args.restart < 1:
        raise ValueError(f"--restart must be in (0,1), got {args.restart}")
    adj = sp.load_npz(args.graph)
    proteins_file = pathlib.Path(args.graph).with_suffix("").with_suffix(".proteins.txt")
    # try alternate naming
    if not proteins_file.exists():
        proteins_file = pathlib.Path(str(args.graph).replace(".npz", ".proteins.txt"))
    if proteins_file.exists():
        gene_list = [l.strip() for l in open(proteins_file) if l.strip()]
        if len(gene_list) != adj.shape[0]:
            print(f"Warning: proteins file length {len(gene_list)} != graph dim {adj.shape[0]}, using synthetic names")
            gene_list = [f"GENE{i}" for i in range(adj.shape[0])]
    else:
        gene_list = [f"GENE{i}" for i in range(adj.shape[0])]
        print(f"Warning: proteins file not found {proteins_file}, using synthetic names")

    W = column_normalize(adj)
    p0 = get_seed_vector(gene_list, SEED_GENES)
    print(f"Seed genes in graph: {(p0>0).sum()}/{len(SEED_GENES)}")
    if p0.sum() == 0:
        raise ValueError("No seed genes found in graph -- check protein->symbol translation (see data_pipeline.string_info)")
    p = random_walk_with_restart(W, p0, restart_prob=args.restart, tol=1e-6)
    out = pathlib.Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.save(out, p)
    print(f"RWR scores saved to {out}, top 5 genes:")
    order = np.argsort(p)[::-1][:5]
    for idx in order:
        print(f"  {gene_list[idx]}: {p[idx]:.6f}")


def cmd_train(args: argparse.Namespace) -> None:
    import pandas as pd

    df = pd.read_parquet(args.features) if args.features.endswith(".parquet") else pd.read_csv(args.features)
    # Expect columns: gene, degree, ... , label
    if "label" not in df.columns:
        raise ValueError("Features file must contain 'label' column (1 for AD seed, 0 otherwise)")
    feature_cols = [c for c in df.columns if c not in ("gene", "label")]
    y = df["label"].values
    model = train_fusion_model(df[feature_cols], y, model_type=args.model_type)
    out = pathlib.Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        pickle.dump({"model": model, "feature_cols": feature_cols}, f)
    print(f"Model saved to {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="AD gene-network pipeline CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("build-graph", help="Build adjacency from STRING file")
    p1.add_argument("--string-path", required=True, help="Path to 9606.protein.links.v12.0.txt.gz")
    p1.add_argument("--output", required=True, help="Output prefix (e.g. /data/graph)")
    p1.add_argument("--threshold", type=int, default=700, help="Combined score threshold 0-1000")
    p1.add_argument("--weighted", action="store_true", help="Use weighted edges")
    p1.set_defaults(func=cmd_build_graph)

    p2 = sub.add_parser("run-rwr", help="Run RWR propagation")
    p2.add_argument("--graph", required=True, help="Path to graph .npz")
    p2.add_argument("--output", required=True, help="Output .npy path")
    p2.add_argument("--restart", type=float, default=0.3, help="Restart probability in (0,1)")
    p2.set_defaults(func=cmd_run_rwr)

    p3 = sub.add_parser("train", help="Train fusion model")
    p3.add_argument("--features", required=True)
    p3.add_argument("--output", required=True)
    p3.add_argument("--model-type", choices=["logistic", "gbt"], default="logistic")
    p3.set_defaults(func=cmd_train)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
