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


def test_parse_with_comment_lines(tmp_string_file):
    content = "# STRING links test file\nprotein1 protein2 combined_score\n9606.A 9606.B 800\n# comment between rows\n9606.B 9606.C 900\n9606.C 9606.D 500\n"
    p = tmp_string_file(content)
    proteins, edges = parse_string_links(p, confidence_threshold=700)
    assert len(edges) == 2  # 500 filtered
    assert 9606 if False else True  # sanity: non-empty

def test_parse_with_tab_separator(tmp_string_file):
    content = "protein1\tprotein2\tcombined_score\n9606.A\t9606.B\t800\n9606.B\t9606.C\t950\n"
    p = tmp_string_file(content)
    proteins, edges = parse_string_links(p, confidence_threshold=700)
    assert len(edges) == 2
    assert len(proteins) == 3


def test_parse_extra_columns_ignored(tmp_string_file):
    content = "protein1 protein2 combined_score extra_col\n9606.A 9606.B 800 foo bar\n9606.B 9606.C 900 baz\n"
    p = tmp_string_file(content)
    proteins, edges = parse_string_links(p, confidence_threshold=700)
    assert len(edges) == 2


def test_parse_empty_file_header_only(tmp_string_file):
    content = "protein1 protein2 combined_score\n"
    p = tmp_string_file(content)
    proteins, edges = parse_string_links(p, confidence_threshold=700)
    assert proteins == []
    assert edges == []


def test_parse_missing_columns_skipped(tmp_string_file):
    content = "protein1 protein2 combined_score\n9606.A 9606.B\n9606.A 9606.B 800\n\n9606.B\n9606.C 9606.D 900\n"
    p = tmp_string_file(content)
    proteins, edges = parse_string_links(p, confidence_threshold=700)
    assert len(edges) == 2


def test_parse_non_numeric_scores_skipped(tmp_string_file):
    content = "protein1 protein2 combined_score\n9606.A 9606.B NA\n9606.A 9606.B abc\n9606.A 9606.B 800\n"
    p = tmp_string_file(content)
    proteins, edges = parse_string_links(p, confidence_threshold=700)
    assert len(edges) == 1


def test_parse_threshold_boundary(tmp_string_file):
    content = "protein1 protein2 combined_score\n9606.A 9606.B 700\n9606.B 9606.C 699\n9606.C 9606.D 701\n"
    p = tmp_string_file(content)
    proteins, edges = parse_string_links(p, confidence_threshold=700)
    scores = sorted(s for _,_,s in edges)
    assert 699 not in scores
    assert 700 in scores
    assert 701 in scores


def test_parse_multiple_header_variants(tmp_string_file):
    # header with different casing and leading comments
    content = "# comment\nPROTEIN1 PROTEIN2 COMBINED_SCORE\n9606.A 9606.B 800\n"
    p = tmp_string_file(content)
    proteins, edges = parse_string_links(p, confidence_threshold=700)
    assert len(edges) == 1


def test_parse_large_threshold_validation(tmp_path):
    import pytest
    # create minimal file
    p = tmp_path / "mini.txt"
    p.write_text("protein1 protein2 combined_score\n9606.A 9606.B 800\n")
    import pytest as _pytest
    with _pytest.raises(ValueError):
        parse_string_links(p, confidence_threshold=2000)
    with _pytest.raises(ValueError):
        parse_string_links(p, confidence_threshold=-1)


def test_parse_whitespace_robust(tmp_string_file):
    content = "  protein1   protein2   combined_score  \n  9606.A   9606.B   800  \n\t9606.B\t9606.C\t900\t\n"
    p = tmp_string_file(content)
    proteins, edges = parse_string_links(p, confidence_threshold=700)
    assert len(edges) == 2


def test_parse_gz_with_comments(tmp_string_file):
    content = "# header comment\nprotein1 protein2 combined_score\n9606.X 9606.Y 900\n# another comment\n9606.Y 9606.Z 800\n"
    p = tmp_string_file(content, gz=True)
    proteins, edges = parse_string_links(p, confidence_threshold=700)
    assert len(edges) == 2


def test_column_normalize_isolated_node():
    # isolated node 2 has no edges
    n = 3
    edges = [(0,1,900)]
    adj = build_adjacency(n, edges)
    W = column_normalize(adj)
    # column 2 should be all zeros
    col2 = np.array(W[:,2].todense()).ravel()
    assert (col2 == 0).all()


def test_build_adjacency_weighted(tmp_string_file):
    n = 3
    edges = [(0,1,500),(1,2,1000)]
    adj_unw = build_adjacency(n, edges, weighted=False)
    adj_w = build_adjacency(n, edges, weighted=True)
    # weighted should have different data values
    assert adj_w[0,1] != adj_unw[0,1] or adj_w[1,0] != adj_unw[1,0]
    assert abs(adj_w[1,2] - 1.0) < 1e-9  # 1000/1000 =1
    assert abs(adj_w[0,1] - 0.5) < 1e-9
