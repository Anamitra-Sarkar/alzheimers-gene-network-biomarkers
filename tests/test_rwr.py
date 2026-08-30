import numpy as np
import scipy.sparse as sp
import pytest

from data_pipeline.rwr import random_walk_with_restart
from data_pipeline.string_parser import build_adjacency, column_normalize
from data_pipeline.seed_genes import get_seed_vector


def test_rwr_converges_and_sums_to_one(seeded_adj_and_W):
    genes, adj, W = seeded_adj_and_W
    # seed at GENE0
    p0 = get_seed_vector(genes, seed_genes=["GENE0"])
    p = random_walk_with_restart(W, p0, restart_prob=0.3, tol=1e-8, max_iter=200)
    assert abs(p.sum() - 1.0) < 1e-6
    assert (p >= 0).all()
    assert p[0] > p[5]  # seed component should rank higher than distant component


def test_rwr_seed_genes_rank_high():
    # Construct two-cliques: clique A contains seed, clique B distant via single bridge
    n = 10
    # clique 0-4 fully connected, clique 5-9 fully connected, bridge 4-5
    edges = []
    for i in range(5):
        for j in range(i+1,5):
            edges.append((i,j,900))
    for i in range(5,10):
        for j in range(i+1,10):
            edges.append((i,j,900))
    edges.append((4,5,700))
    adj = build_adjacency(n, edges)
    W = column_normalize(adj)
    genes = [f"GENE{i}" for i in range(n)]
    p0 = get_seed_vector(genes, seed_genes=["GENE0"])
    p = random_walk_with_restart(W, p0, restart_prob=0.3)
    # nodes in same clique as seed should have higher scores than distant clique
    mean_clique_A = p[0:5].mean()
    mean_clique_B = p[5:10].mean()
    assert mean_clique_A > mean_clique_B
    # seed itself highest
    assert p[0] == p.max()


def test_rwr_zero_p0_raises(seeded_adj_and_W):
    genes, adj, W = seeded_adj_and_W
    p0 = np.zeros(len(genes))
    with pytest.raises(ValueError):
        random_walk_with_restart(W, p0)


def test_rwr_restart_range_validation(seeded_adj_and_W):
    genes, adj, W = seeded_adj_and_W
    p0 = get_seed_vector(genes, seed_genes=["GENE0"])
    with pytest.raises(ValueError):
        random_walk_with_restart(W, p0, restart_prob=1.0)
    with pytest.raises(ValueError):
        random_walk_with_restart(W, p0, restart_prob=0)


def test_rwr_empty_graph():
    W = sp.csc_matrix((0,0))
    p0 = np.array([])
    p = random_walk_with_restart(W, p0)
    assert len(p) == 0


def test_rwr_trajectory_return(seeded_adj_and_W):
    genes, adj, W = seeded_adj_and_W
    p0 = get_seed_vector(genes, seed_genes=["GENE1"])
    p, traj = random_walk_with_restart(W, p0, return_trajectory=True)
    assert len(traj) >= 2
    assert traj[0].tolist() == p0.tolist()


def test_rwr_with_different_restart():
    n = 6
    edges = [(0,1,900),(1,2,900),(2,3,900),(3,4,900),(4,5,900)]
    adj = build_adjacency(n, edges)
    W = column_normalize(adj)
    genes = [f"GENE{i}" for i in range(n)]
    p0 = get_seed_vector(genes, seed_genes=["GENE0"])
    p_low = random_walk_with_restart(W, p0, restart_prob=0.15)
    p_high = random_walk_with_restart(W, p0, restart_prob=0.7)
    # higher restart keeps more mass near seed
    assert p_high[0] > p_low[0]
