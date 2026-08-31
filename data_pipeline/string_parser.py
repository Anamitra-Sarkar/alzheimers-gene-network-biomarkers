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
        confidence_threshold: retain edges with combined_score >= threshold (0-1000)

    Returns:
        (proteins, edges) where proteins is sorted list of unique protein IDs,
        edges is list of (i, j, score) with i/j indices into proteins list.
        Undirected edges appear once; self-loops are dropped.

    Real-file quirks handled:
        - plain text vs gzipped (.gz / .txt.gz) via suffix detection
        - optional header row (protein1/protein2/combined_score, any casing)
        - comment lines starting with '#'
        - tab or space separated columns, extra trailing columns ignored
        - missing optional columns / malformed rows skipped (not crashed)
        - empty file (header only) returns empty graph honestly
    """
    if not 0 <= confidence_threshold <= 1000:
        raise ValueError(f"confidence_threshold must be in [0,1000], got {confidence_threshold}")

    path = pathlib.Path(path)
    if not path.exists():
        raise FileNotFoundError(f"STRING file not found: {path}. "
                                "Download via: https://stringdb-downloads.org/download/protein.links.v12.0/9606.protein.links.v12.0.txt.gz "
                                "and pass --string-path <local file>")

    # Robust gz detection: handle both .gz and .txt.gz (Path.suffix gives only last suffix)
    is_gz = path.suffix == ".gz" or "".join(path.suffixes).endswith(".gz")
    opener = gzip.open if is_gz else open  # type: ignore[assignment]

    proteins_set: set[str] = set()
    raw_edges: list[Tuple[str, str, int]] = []

    with opener(path, "rt") as f:  # type: ignore[call-arg]
        # Read all non-empty, non-comment lines, detect header robustly
        raw_lines: list[str] = []
        header_found = False
        for raw in f:
            stripped = raw.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                continue
            low = stripped.lower()
            # header detection: any line containing protein1 or (protein and combined_score)
            if not header_found and ("protein1" in low or ("protein" in low and "combined_score" in low) or "string_protein" in low):
                header_found = True
                continue
            # Also skip a header that slipped through as first line with non-numeric score column
            # We detect header before collecting; no need to add header line
            raw_lines.append(stripped)

        # Fallback: if we never saw a header but first token looks like header (e.g. "protein1"),
        # the loop already skipped it. If file had only header, raw_lines will be empty -> honest empty graph.

        for line in raw_lines:
            # Skip comment lines that may have leading whitespace before '#'
            if line.lstrip().startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 3:
                continue
            p1, p2, score_s = parts[0], parts[1], parts[2]
            if not p1 or not p2:
                continue
            if p1 == p2:
                continue
            try:
                score = int(score_s)
            except ValueError:
                # Handle scores like "732.0" or trailing comments after score
                try:
                    score = int(float(score_s))
                except ValueError:
                    continue
            if not 0 <= score <= 1000:
                # Clamp-beyond-range or malformed; skip if absurd
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
