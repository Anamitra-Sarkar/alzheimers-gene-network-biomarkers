"""
STRING protein.info parser: maps STRING protein IDs (e.g. '9606.ENSP00000000233')
to gene symbols ('preferred_name' column). Real, documented source:
https://stringdb-downloads.org/download/protein.info.v12.0/9606.protein.info.v12.0.txt.gz

Needed because `parse_string_links` (string_parser.py) returns raw STRING protein IDs,
while `SEED_GENES` (seed_genes.py) is a list of gene symbols -- without this mapping,
`get_seed_vector` finds zero matches and `random_walk_with_restart` raises
"p0 is all zeros: no seed genes in graph" on any real run.
"""
from __future__ import annotations

import gzip
import pathlib


def parse_string_info(path: str | pathlib.Path) -> dict[str, str]:
    """Parse STRING protein.info file -> dict protein_id -> gene symbol (preferred_name)."""
    path = pathlib.Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"STRING protein.info file not found: {path}. Download via: "
            "https://stringdb-downloads.org/download/protein.info.v12.0/9606.protein.info.v12.0.txt.gz"
        )
    opener = gzip.open if path.suffix == ".gz" else open
    mapping: dict[str, str] = {}
    with opener(path, "rt") as f:  # type: ignore
        header = f.readline().strip().split("\t")
        col_idx = {h: i for i, h in enumerate(header)}
        pid_i = col_idx.get("#string_protein_id", col_idx.get("string_protein_id", 0))
        name_i = col_idx.get("preferred_name", 1)
        for line in f:
            if not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) <= max(pid_i, name_i):
                continue
            mapping[parts[pid_i]] = parts[name_i]
    return mapping


def translate_gene_list(protein_ids: list[str], id_to_symbol: dict[str, str]) -> list[str]:
    """
    Translate a list of STRING protein IDs to gene symbols where a mapping exists;
    falls back to the raw protein ID (uppercased) for anything unmapped so no gene
    silently disappears from downstream indexing.
    """
    return [id_to_symbol.get(pid, pid) for pid in protein_ids]
