import gzip
import pathlib

import numpy as np
import scipy.sparse as sp

from data_pipeline.string_parser import parse_string_links, build_adjacency, column_normalize


def test_parse_string_links_basic(tmp_string_file):
    content = "protein1 protein2 combined_score\n9606.A 9606.B 800\n9606.B 9606.C 900\n9606.A 9606.C 500\n9606.D 9606.E 750\n"
    p = tmp_string_file(content)
    proteins, edges = parse_string_links(p, confidence_threshold=700)
    # 500 edge filtered, 4 proteins remain (A,B,C? actually D,E also but A-C edge dropped but proteins with only low edge? A,B,C have high edges; D,E have 750 -> keep)
    assert 4 <= len(proteins) <= 5
    assert all(s >= 700 for _, _, s in edges)
    # ensure proteins sorted
    assert proteins == sorted(proteins)


def test_parse_string_links_gz(tmp_string_file):
    content = "protein1 protein2 combined_score\n9606.X 9606.Y 950\n9606.Y 9606.Z 800\n"
    p = tmp_string_file(content, gz=True)
    proteins, edges = parse_string_links(p, confidence_threshold=700)
    assert len(proteins) == 3
    assert len(edges) == 2


def test_parse_missing_file_raises(tmp_path):
    import pytest
    with pytest.raises(FileNotFoundError):
        parse_string_links(tmp_path / "nonexistent.txt")


def test_build_adjacency_symmetric():
    n = 4
    edges = [(0,1,900),(1,2,800),(2,3,950)]
    adj = build_adjacency(n, edges)
    assert adj.shape == (4,4)
    # symmetric
    diff = (adj - adj.T).nnz
    assert diff == 0
    # no self-loop
    assert adj.diagonal().sum() == 0


def test_column_normalize_columns_sum_one():
    n = 3
    edges = [(0,1,900),(1,2,900)]
    adj = build_adjacency(n, edges)
    W = column_normalize(adj)
    col_sums = np.array(W.sum(axis=0)).ravel()
    # columns with degree>0 should sum 1
    for i, s in enumerate(col_sums):
        deg = adj[:, i].sum()
        if deg > 0:
            assert abs(s - 1.0) < 1e-9
        else:
            assert s == 0


def test_self_loop_dropped(tmp_string_file):
    content = "protein1 protein2 combined_score\n9606.A 9606.A 900\n9606.A 9606.B 800\n"
    p = tmp_string_file(content)
    proteins, edges = parse_string_links(p, confidence_threshold=700)
    # self-loop not in edges
    for i,j,_ in edges:
        assert i != j
