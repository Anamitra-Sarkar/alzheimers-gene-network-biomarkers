import numpy as np
import scipy.sparse as sp

from data_pipeline.string_parser import build_adjacency
from data_pipeline.features import compute_features


def test_compute_features_columns():
    n = 10
    edges = [(0,1,900),(1,2,900),(2,3,900),(0,2,800),(5,6,900),(6,7,900)]
    adj = build_adjacency(n, edges)
    genes = [f"GENE{i}" for i in range(n)]
    rwr = np.random.rand(n)
    rwr /= rwr.sum()
    df = compute_features(adj, genes, rwr_scores=rwr)
    expected_cols = {"gene","degree","degree_norm","pagerank","betweenness","closeness","rwr_score"}
    assert expected_cols.issubset(set(df.columns))
    assert len(df) == n
    # degree for isolated node =0
    iso = df[df["gene"]=="GENE9"].iloc[0]
    assert iso["degree"] == 0
    # degree_norm in [0,1]
    assert df["degree_norm"].between(0,1).all()
    # pagerank sums to ~1
    assert abs(df["pagerank"].sum() - 1.0) < 1e-6
    # betweenness in [0,1]
    assert df["betweenness"].between(0,1).all()
    # closeness non-negative
    assert (df["closeness"] >= 0).all()


def test_compute_features_empty():
    adj = sp.csr_matrix((0,0))
    df = compute_features(adj, [])
    assert len(df) == 0


def test_compute_features_star():
    # star graph: center degree 9, leaves 1
    n = 10
    edges = [(0,i,900) for i in range(1,10)]
    adj = build_adjacency(n, edges)
    genes = [f"GENE{i}" for i in range(n)]
    df = compute_features(adj, genes)
    center = df[df["gene"]=="GENE0"].iloc[0]
    leaf = df[df["gene"]=="GENE1"].iloc[0]
    assert center["degree"] > leaf["degree"]
    assert center["betweenness"] > leaf["betweenness"]


def test_compute_features_without_rwr():
    n = 5
    edges = [(0,1,900),(1,2,900)]
    adj = build_adjacency(n, edges)
    genes = [f"GENE{i}" for i in range(n)]
    df = compute_features(adj, genes)
    assert "rwr_score" not in df.columns
