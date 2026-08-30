"""
Per-gene feature computation for fusion model.

Computes:
 - degree (normalized)
 - PageRank centrality (power iteration via networkx or scipy)
 - Betweenness (approximate when graph is large; exact for small fixture graphs)
 - Closeness (or harmonic centrality for disconnected graphs)
All features returned as DataFrame / ndarray ready for sklearn.
Documented tradeoff: betweenness O(n*m) — we use k-sample approximation for n>500.
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp

try:
    import networkx as nx
except ImportError:
    nx = None  # type: ignore

import pandas as pd


def compute_features(
    adj: sp.spmatrix,
    gene_list: list[str],
    rwr_scores: np.ndarray | None = None,
    betweenness_k: int | None = None,
) -> pd.DataFrame:
    """
    Compute topology features for each gene.

    Args:
        adj: sparse adjacency matrix (n x n), symmetric
        gene_list: gene/protein IDs aligned with adj rows
        rwr_scores: optional RWR steady-state vector to include as feature
        betweenness_k: if set, use k-sample approximation; if None auto:
                       exact if n<=500 else k=min(100, n)

    Returns:
        DataFrame with columns: gene, degree, degree_norm, pagerank, betweenness, closeness, [rwr_score]
    """
    n = adj.shape[0]
    if n == 0:
        return pd.DataFrame()
    if len(gene_list) != n:
        raise ValueError("gene_list length mismatch")

    # Degree
    degree = np.array(adj.sum(axis=1)).ravel().astype(float)
    max_deg = degree.max() if degree.max() > 0 else 1.0
    degree_norm = degree / max_deg

    # Build NetworkX graph for centrality measures
    # For small graphs exact; for large graphs still feasible via networkx's optimized algorithms
    G = _adj_to_networkx(adj, gene_list)

    # PageRank (use networkx)
    if G.number_of_nodes() > 0:
        # Use networkx pagerank (handles disconnected)
        try:
            pr_dict = nx.pagerank(G, alpha=0.85, max_iter=100, tol=1e-6)
        except Exception:
            # fallback: uniform
            pr_dict = {g: 1.0 / n for g in gene_list}
        pagerank = np.array([pr_dict.get(g, 0.0) for g in gene_list], dtype=float)
    else:
        pagerank = np.zeros(n)

    # Betweenness: exact for small, sampled for large
    if n <= 500 and betweenness_k is None:
        k_eff = None
    else:
        k_eff = betweenness_k if betweenness_k is not None else min(100, n)

    try:
        if k_eff is None:
            btw_dict = nx.betweenness_centrality(G, normalized=True)
        else:
            # sampled approximation
            btw_dict = nx.betweenness_centrality(G, k=k_eff, normalized=True, seed=42)
    except Exception:
        btw_dict = {g: 0.0 for g in gene_list}
    betweenness = np.array([btw_dict.get(g, 0.0) for g in gene_list], dtype=float)

    # Closeness / harmonic centrality (works for disconnected)
    try:
        # harmonic is better for disconnected than closeness
        harm_dict = nx.harmonic_centrality(G)
        # normalize by (n-1) to keep in [0,1]
        if n > 1:
            harm_vals = np.array([harm_dict.get(g, 0.0) for g in gene_list], dtype=float) / (n - 1)
        else:
            harm_vals = np.array([0.0] * n)
    except Exception:
        harm_vals = np.zeros(n)
    # Also compute closeness for naming; store harmonic as 'closeness'
    closeness = harm_vals

    df = pd.DataFrame({
        "gene": gene_list,
        "degree": degree,
        "degree_norm": degree_norm,
        "pagerank": pagerank,
        "betweenness": betweenness,
        "closeness": closeness,
    })
    if rwr_scores is not None:
        if len(rwr_scores) != n:
            raise ValueError("rwr_scores length mismatch")
        df["rwr_score"] = rwr_scores
    return df


def _adj_to_networkx(adj: sp.spmatrix, gene_list: list[str]) -> "nx.Graph":
    """Convert sparse adjacency to NetworkX graph with gene labels."""
    import networkx as nx

    n = adj.shape[0]
    G = nx.Graph()
    G.add_nodes_from(gene_list)
    # iterate over upper triangle to avoid double-adding
    coo = adj.tocoo()
    for i, j, w in zip(coo.row, coo.col, coo.data):
        if i < j:  # add once, Graph is undirected
            G.add_edge(gene_list[i], gene_list[j], weight=float(w))
        elif i == j:
            continue
    # For symmetry with duplicates, ensure all edges where i!=j
    # The above covers all since we filtered i<j but coo contains both directions for our builder
    # Need to deduplicate: if adj symmetric, we add each edge twice unless filtered; our filter i<j ensures one copy.
    return G
