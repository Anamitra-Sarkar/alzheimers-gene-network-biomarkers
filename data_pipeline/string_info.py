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
    """Parse STRING protein.info file -> dict protein_id -> gene symbol (preferred_name).

    Real file quirks handled:
        - plain text vs gzipped (.gz / .txt.gz)
        - tab or space separated header detection, any casing
        - comment lines starting with '#'
        - header names: #string_protein_id or string_protein_id (with leading #)
        - extra columns beyond preferred_name ignored
        - empty / header-only files return empty dict honestly
        - rows with missing columns skipped (not crashed)
    """
    path = pathlib.Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"STRING protein.info file not found: {path}. Download via: "
            "https://stringdb-downloads.org/download/protein.info.v12.0/9606.protein.info.v12.0.txt.gz"
        )
    is_gz = path.suffix == ".gz" or "".join(path.suffixes).endswith(".gz")
    opener = gzip.open if is_gz else open  # type: ignore[assignment]
    mapping: dict[str, str] = {}
    with opener(path, "rt") as f:  # type: ignore
        # Find header line (skip leading comments/empty lines)
        header_line: str | None = None
        header = []
        col_idx: dict[str, int] = {}
        pid_i = 0
        name_i = 1
        header_found = False
        # We need to peek through file to find header; buffer the rest
        remaining: list[str] = []
        for raw in f:
            stripped = raw.strip()
            if not stripped:
                continue
            if stripped.startswith("#") and not header_found:
                # Header line itself starts with #string_protein_id
                header_line = stripped
                # Parse header even if it starts with '#'
                header = [h.lstrip("#") for h in header_line.split("\t")]
                # Fallback if split by tabs gives single column with spaces
                if len(header) == 1 and " " in header[0]:
                    header = header_line.lstrip("#").split()
                # Also handle space-separated case without tabs
                if len(header) == 1:
                    header = header_line.lstrip("#").split()
                col_idx = {h.strip().lower(): i for i, h in enumerate(header)}
                # Try multiple name variants
                pid_candidates = ["#string_protein_id", "string_protein_id", "protein_id", "protein"]
                name_candidates = ["preferred_name", "preferredname", "gene", "symbol"]
                pid_i = next((col_idx[c] for c in pid_candidates if c in col_idx), 0)
                name_i = next((col_idx[c] for c in name_candidates if c in col_idx), 1 if len(header) > 1 else 0)
                # Validate we have at least protein-like column
                if "string_protein_id" in col_idx or "protein_id" in col_idx or "preferred_name" in col_idx:
                    header_found = True
                    continue
                # If this # line was not header, treat as comment
                continue
            if not header_found:
                # Header without leading # (e.g. "protein1 ..." unlikely for info file but handle)
                low = stripped.lower()
                if "string_protein_id" in low or "preferred_name" in low:
                    header_line = stripped
                    header = stripped.lstrip("#").split("\t")
                    if len(header) == 1:
                        header = stripped.lstrip("#").split()
                    header = [h.lstrip("#") for h in header]
                    col_idx = {h.strip().lower(): i for i, h in enumerate(header)}
                    pid_i = next((col_idx[c] for c in ["string_protein_id", "protein_id", "protein"] if c in col_idx), 0)
                    name_i = next((col_idx[c] for c in ["preferred_name", "preferredname"] if c in col_idx), 1)
                    header_found = True
                    continue
                # If no header yet but line looks like data (contains ENSP), assume default columns
                if "ENSP" in stripped:
                    header_found = True
                    remaining.append(stripped)
                    # default indices already set (0,1)
                    continue
            # Data line
            if stripped.startswith("#"):
                continue
            remaining.append(stripped)

        # If we never parsed a header but have no remaining, try to have defaults
        # Now process remaining as data
        for line in remaining:
            if not line.strip():
                continue
            if line.lstrip().startswith("#"):
                continue
            # Try tab split first (real file is tab-separated), fall back to whitespace
            parts = line.split("\t")
            if len(parts) <= max(pid_i, name_i):
                parts = line.split()
            if len(parts) <= max(pid_i, name_i):
                continue
            pid = parts[pid_i].strip()
            name = parts[name_i].strip()
            if not pid or not name:
                continue
            mapping[pid] = name
    return mapping


def translate_gene_list(protein_ids: list[str], id_to_symbol: dict[str, str]) -> list[str]:
    """
    Translate a list of STRING protein IDs to gene symbols where a mapping exists;
    falls back to the raw protein ID (uppercased) for anything unmapped so no gene
    silently disappears from downstream indexing.
    """
    return [id_to_symbol.get(pid, pid) for pid in protein_ids]
