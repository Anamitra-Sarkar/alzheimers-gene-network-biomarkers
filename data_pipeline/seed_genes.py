"""
Hard-coded Alzheimer's disease seed gene list.

Curated from established AD GWAS and genetics literature.
Each entry includes primary genetic evidence type.
All genes are well-known AD risk / causal genes in the public domain;
no download required. Citations are documented in docs/data_sources.md.
"""

from __future__ import annotations

SEED_GENE_INFO: dict[str, dict[str, str]] = {
    # Mendelian / early-onset causal genes
    "APOE": {"full_name": "Apolipoprotein E", "evidence": "GWAS + Mendelian risk, chr19q13.32, strongest late-onset AD risk locus", "pmid": "1377412; 30617256"},
    "APP": {"full_name": "Amyloid Precursor Protein", "evidence": "Mendelian early-onset AD, amyloid cascade", "pmid": "1671712"},
    "PSEN1": {"full_name": "Presenilin 1", "evidence": "Mendelian early-onset AD, gamma-secretase", "pmid": "7651536"},
    "PSEN2": {"full_name": "Presenilin 2", "evidence": "Mendelian early-onset AD, gamma-secretase", "pmid": "7651536"},
    # Major GWAS loci (Lambert et al. 2013, Kunkle et al. 2019, Bellenguez et al. 2022)
    "TREM2": {"full_name": "Triggering Receptor Expressed On Myeloid Cells 2", "evidence": "GWAS + rare variant, microglial, R47H", "pmid": "23150934; 30617256"},
    "CLU": {"full_name": "Clusterin (Apolipoprotein J)", "evidence": "GWAS (Lambert 2009, 2013)", "pmid": "19734903; 24162737"},
    "CR1": {"full_name": "Complement Receptor 1", "evidence": "GWAS (Lambert 2009, 2013)", "pmid": "19734903"},
    "PICALM": {"full_name": "Phosphatidylinositol Binding Clathrin Assembly Protein", "evidence": "GWAS (Harold 2009, Lambert 2013)", "pmid": "19734902"},
    "BIN1": {"full_name": "Bridging Integrator 1", "evidence": "GWAS, top locus after APOE", "pmid": "19734903; 30617256"},
    "ABCA7": {"full_name": "ATP Binding Cassette Subfamily A Member 7", "evidence": "GWAS (Hollingworth 2011, Kunkle 2019)", "pmid": "21460841"},
    "SORL1": {"full_name": "Sortilin Related Receptor 1", "evidence": "GWAS + candidate, retromer sorting", "pmid": "21460841; 30617256"},
    "CD33": {"full_name": "CD33 Molecule (Siglec-3)", "evidence": "GWAS (Hollingworth 2011, Naj 2011)", "pmid": "21460841"},
    "MS4A6A": {"full_name": "Membrane Spanning 4-Domains A6A", "evidence": "GWAS MS4A cluster (Hollingworth 2011)", "pmid": "21460841"},
    "ADAM10": {"full_name": "ADAM Metallopeptidase Domain 10", "evidence": "GWAS + rare variant, alpha-secretase", "pmid": "24162737; 30617256"},
    "PLCG2": {"full_name": "Phospholipase C Gamma 2", "evidence": "GWAS rare protective variant P522R", "pmid": "29093296; 30617256"},
    # Additional well-validated loci
    "CD2AP": {"full_name": "CD2 Associated Protein", "evidence": "GWAS (Naj 2011)", "pmid": "21460841"},
    "EPHA1": {"full_name": "EPH Receptor A1", "evidence": "GWAS (Hollingworth 2011)", "pmid": "21460841"},
    "HLA-DRB1": {"full_name": "HLA Class II DRB1", "evidence": "GWAS HLA locus (Lambert 2013)", "pmid": "24162737"},
    "MEF2C": {"full_name": "Myocyte Enhancer Factor 2C", "evidence": "GWAS (Lambert 2013)", "pmid": "24162737"},
    "INPP5D": {"full_name": "Inositol Polyphosphate-5-Phosphatase D", "evidence": "GWAS (Lambert 2013)", "pmid": "24162737"},
    "FERMT2": {"full_name": "Fermitin Family Member 2", "evidence": "GWAS (Lambert 2013)", "pmid": "24162737"},
    "CELF1": {"full_name": "CUGBP Elav-Like Family Member 1", "evidence": "GWAS (Lambert 2013)", "pmid": "24162737"},
    "NME8": {"full_name": "NME/NM23 Family Member 8", "evidence": "GWAS (Lambert 2013)", "pmid": "24162737"},
    "CASS4": {"full_name": "Cas Scaffolding Molecule Family Member 4", "evidence": "GWAS (Lambert 2013)", "pmid": "24162737"},
    "SPI1": {"full_name": "Spi-1 Proto-Oncogene (PU.1)", "evidence": "GWAS (Huang 2017, Kunkle 2019), myeloid TF", "pmid": "30617256"},
    "ACE": {"full_name": "Angiotensin I Converting Enzyme", "evidence": "GWAS / candidate, vascular", "pmid": "30617256"},
}

# Ordered list for deterministic iteration
SEED_GENES: list[str] = list(SEED_GENE_INFO.keys())


def get_seed_vector(gene_list: list[str], seed_genes: list[str] | None = None) -> "np.ndarray":
    """
    Build p0 seed vector: uniform over seeds present in gene_list, zero elsewhere.
    Sums to 1. Returns zeros if no overlap.
    """
    import numpy as np

    if seed_genes is None:
        seed_genes = SEED_GENES
    seed_set = set(s.upper() for s in seed_genes)
    vec = np.zeros(len(gene_list), dtype=float)
    for i, g in enumerate(gene_list):
        if g.upper() in seed_set:
            vec[i] = 1.0
    s = vec.sum()
    if s > 0:
        vec /= s
    return vec


def get_seed_genes_present(gene_list: list[str], seed_genes: list[str] | None = None) -> list[str]:
    """Return seed genes that appear in gene_list (case-insensitive)."""
    if seed_genes is None:
        seed_genes = SEED_GENES
    seed_set = set(s.upper() for s in seed_genes)
    return [g for g in gene_list if g.upper() in seed_set]
