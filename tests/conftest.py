"""Shared fixtures: small synthetic graphs (10-50 nodes) for testing."""

import gzip
import pathlib
import tempfile

import numpy as np
import pytest
import scipy.sparse as sp


@pytest.fixture
def small_gene_list():
    return [f"GENE{i}" for i in range(10)]


@pytest.fixture
def tiny_line_graph():
    """Line graph 0-1-2-3-4, 5 isolated clique, for predictable RWR."""
    n = 10
    edges = []
    for i in range(4):
        edges.append((i, i+1, 900))
    # extra edges to give structure
    edges.extend([(0,2,800),(1,3,800),(5,6,900),(6,7,900),(7,8,900),(8,9,900),(5,7,800)])
    return n, edges


@pytest.fixture
def star_graph():
    """Star centered at 0 with leaves 1..9."""
    n = 10
    edges = [(0, i, 900) for i in range(1,10)]
    return n, edges


@pytest.fixture
def seeded_adj_and_W(tiny_line_graph):
    from data_pipeline.string_parser import build_adjacency, column_normalize
    n, edges = tiny_line_graph
    adj = build_adjacency(n, edges)
    W = column_normalize(adj)
    genes = [f"GENE{i}" for i in range(n)]
    return genes, adj, W


@pytest.fixture
def tmp_string_file(tmp_path):
    """Helper to create a tiny STRING-format file for parser tests."""
    def _make(content: str, gz: bool = False):
        p = tmp_path / ("test.txt.gz" if gz else "test.txt")
        if gz:
            with gzip.open(p, "wt") as f:
                f.write(content)
        else:
            p.write_text(content)
        return p
    return _make
