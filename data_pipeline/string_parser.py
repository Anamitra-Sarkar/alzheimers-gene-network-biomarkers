"""
STRING PPI network parser.

Real data source:
  - Download: https://stringdb-downloads.org/download/protein.links.v12.0/9606.protein.links.v12.0.txt.gz
    (human, 9606, ~19k proteins, ~11M edges at all confidence thresholds)
  - API: https://string-db.org/api/
  - Mapping: https://stringdb-downloads.org/download/protein.aliases.v12.0/9606.protein.aliases.v12.0.txt.gz

We filter to combined_score >= 700 (high confidence) for a manageable graph.
In sandbox tests we use small synthetic fixtures instead of the real download.

File format (9606.protein.links.v12.0.txt):
  protein1  protein2  combined_score   (space-separated, header row)
  e.g. 9606.ENSP00000000233  9606.ENSP00000312345  732
"""

from __future__ import annotations

import gzip
import pathlib
from typing import Tuple

import numpy as np
import scipy.sparse as sp


def download_string_ppi(url: str, dest: pathlib.Path) -> pathlib.Path:
    """
    Download STRING PPI file from URL to dest.
    Real usage: url = "https://stringdb-downloads.org/download/protein.links.v12.0/9606.protein.links.v12.0.txt.gz"
    Requires network access (Kaggle/Modal real run). Not executed in sandbox tests.
    """
    import urllib.request

    dest = pathlib.Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, dest)
    return dest


def parse_string_links(
    path: str | pathlib.Path,
    confidence_threshold: int = 700,
) -> Tuple[list[str], list[Tuple[int, int, int]]]:
    """
    Parse a STRING protein.links file (plain or gzipped).

    Args:
        path: path to .txt or .txt.gz file. Format: header + rows "protein1 protein2 combined_score"
        confidence_threshold: retain edges with combined_score >= threshold

    Returns:
        (proteins, edges) where proteins is sorted list of unique protein IDs,
        edges is list of (i, j, score) with i/j indices into proteins list.
        Undirected edges appear once; self-loops are dropped.
    """
    path = pathlib.Path(path)
    if not path.exists():
        raise FileNotFoundError(f"STRING file not found: {path}. "
                                "Download via: https://stringdb-downloads.org/download/protein.links.v12.0/9606.protein.links.v12.0.txt.gz "
                                "and pass --string-path <local file>")

    opener = gzip.open if path.suffix == ".gz" else open

    proteins_set: set[str] = set()
    raw_edges: list[Tuple[str, str, int]] = []

    with opener(path, "rt") as f:
        header = f.readline()
        # detect header
        has_header = "protein1" in header.lower() or "protein" in header.lower()
        lines = [] if has_header else [header]
        lines += f.readlines()

        for line in lines:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 3:
                continue
            p1, p2, score_s = parts[0], parts[1], parts[2]
            if p1 == p2:
                continue
            try:
                score = int(score_s)
            except ValueError:
                continue
            if score < confidence_threshold:
                continue
            proteins_set.add(p1)
            proteins_set.add(p2)
            raw_edges.append((p1, p2, score))

    proteins = sorted(proteins_set)
    idx = {p: i for i, p in enumerate(proteins)}
    edges = [(idx[a], idx[b], s) for a, b, s in raw_edges]
    return proteins, edges


def build_adjacency(
    num_nodes: int,
    edges: list[Tuple[int, int, int]],
    weighted: bool = False,
) -> sp.csr_matrix:
    """
    Build symmetric sparse adjacency matrix from edge list.

    Args:
        num_nodes: number of nodes
        edges: list of (i, j, score)
        weighted: if True use combined_score as weight (normalized 0-1), else binary 1

    Returns:
        csr_matrix shape (n, n), symmetric, zero diagonal.
    """
    if num_nodes == 0:
        return sp.csr_matrix((0, 0))

    rows: list[int] = []
    cols: list[int] = []
    data: list[float] = []

    for i, j, score in edges:
        w = (score / 1000.0) if weighted else 1.0
        rows.extend([i, j])
        cols.extend([j, i])
        data.extend([w, w])

    mat = sp.coo_matrix((data, (rows, cols)), shape=(num_nodes, num_nodes))
    # combine duplicates by summing (coo -> csr does this)
    mat = mat.tocsr()
    # ensure zero diagonal
    mat.setdiag(0)
    mat.eliminate_zeros()
    return mat


def column_normalize(adj: sp.spmatrix) -> sp.csc_matrix:
    """
    Column-normalize adjacency to obtain transition matrix W where W[i,j] = A[i,j]/deg(j).
    Isolated nodes (deg 0) remain zero column. Returns CSC for efficient column ops in RWR.
    """
    if adj.shape[0] == 0:
        return sp.csc_matrix(adj.shape)

    csc = adj.tocsc()
    # column sums
    col_sums = np.array(csc.sum(axis=0)).ravel()
    # avoid division by zero
    inv = np.divide(1.0, col_sums, out=np.zeros_like(col_sums, dtype=float), where=col_sums != 0)
    # scale columns: W = A * D^{-1}
    # Use sparse diagonal multiplication
    Dinv = sp.diags(inv)
    W = csc @ Dinv
    return W.tocsc()
