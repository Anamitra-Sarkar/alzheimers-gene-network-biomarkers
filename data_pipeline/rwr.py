"""
Random Walk with Restart (RWR) network propagation.

Implements sparse RWR: p_{t+1} = (1 - r) * W * p_t + r * p_0
where W is column-normalized transition matrix, r is restart probability.

Convergence: iterate until L1 change < tol or max_iter reached.
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp


def random_walk_with_restart(
    W: sp.spmatrix,
    p0: np.ndarray,
    restart_prob: float = 0.3,
    tol: float = 1e-6,
    max_iter: int = 100,
    return_trajectory: bool = False,
) -> np.ndarray | tuple[np.ndarray, list[np.ndarray]]:
    """
    Run RWR from seed distribution p0 over transition matrix W.

    Args:
        W: column-normalized transition matrix (n x n), sparse CSC/CSR
        p0: initial distribution (n,), sums to 1. Uniform over seed genes.
        restart_prob: r in [0,1], restart probability (typical 0.15-0.3)
        tol: L1 convergence threshold
        max_iter: maximum iterations
        return_trajectory: if True also return trajectory list

    Returns:
        p: steady-state distribution (n,) summing to ~1
    """
    n = W.shape[0]
    if n == 0:
        return np.array([])
    if p0.shape[0] != n:
        raise ValueError(f"p0 length {p0.shape[0]} != graph size {n}")
    s = p0.sum()
    if s == 0:
        raise ValueError("p0 is all zeros: no seed genes in graph")
    # normalize p0 to sum 1
    p0 = p0 / s

    if not 0 < restart_prob < 1:
        raise ValueError("restart_prob must be in (0,1)")

    # ensure sparse format efficient for matvec
    if sp.issparse(W):
        Wc = W.tocsc() if not isinstance(W, sp.csc_matrix) else W
    else:
        Wc = sp.csc_matrix(W)

    p = p0.copy()
    trajectory = [p.copy()] if return_trajectory else None

    for _ in range(max_iter):
        p_next = (1 - restart_prob) * (Wc @ p) + restart_prob * p0
        # numerical: ensure sum ~1 (column-stochastic preserves mass except leaks from dangling nodes)
        # Re-normalize to handle mass loss from dangling nodes? Standard RWR re-injects via restart;
        # leaked mass will remain <1. We keep raw value (honest). But ensure non-negative.
        p_next = np.maximum(p_next, 0)
        # L1
        diff = np.abs(p_next - p).sum()
        p = p_next
        if return_trajectory:
            trajectory.append(p.copy())
        if diff < tol:
            break

    # Normalize to sum 1 for comparability (optional but expected for ranking)
    # We do NOT force if graph has isolated nodes; instead normalize anyway for reporting
    total = p.sum()
    if total > 0:
        p = p / total

    if return_trajectory:
        return p, trajectory  # type: ignore
    return p


def rwr_scores_for_genes(
    W: sp.spmatrix,
    gene_list: list[str],
    seed_genes: list[str],
    restart_prob: float = 0.3,
    tol: float = 1e-6,
    max_iter: int = 100,
) -> dict[str, float]:
    """Convenience: run RWR and return gene -> score dict."""
    from data_pipeline.seed_genes import get_seed_vector

    p0 = get_seed_vector(gene_list, seed_genes)
    p = random_walk_with_restart(W, p0, restart_prob=restart_prob, tol=tol, max_iter=max_iter)
    return {g: float(s) for g, s in zip(gene_list, p)}
