import numpy as np
import pytest

from data_pipeline.seed_genes import SEED_GENES, SEED_GENE_INFO, get_seed_vector


def test_seed_list_has_required_genes():
    required = ["APOE","APP","PSEN1","PSEN2","TREM2","CLU","CR1","PICALM","BIN1","ABCA7","SORL1","CD33","MS4A6A","ADAM10","PLCG2"]
    for g in required:
        assert g in SEED_GENES, f"Missing seed {g}"
    assert len(SEED_GENES) >= 20


def test_seed_info_has_metadata():
    for g in SEED_GENES:
        assert g in SEED_GENE_INFO
        assert "evidence" in SEED_GENE_INFO[g]
        assert "pmid" in SEED_GENE_INFO[g]


def test_get_seed_vector_uniform():
    genes = ["APOE","BRCA1","TREM2","TP53","BIN1"]
    vec = get_seed_vector(genes)
    assert abs(vec.sum() - 1.0) < 1e-9
    # APOE, TREM2, BIN1 are seeds -> 3 seeds
    assert vec[0] > 0 and vec[2] > 0 and vec[4] > 0
    assert vec[1] == 0 and vec[3] == 0
    assert abs(vec[0] - vec[2]) < 1e-9


def test_get_seed_vector_no_overlap():
    genes = ["BRCA1","TP53"]
    vec = get_seed_vector(genes)
    assert vec.sum() == 0


def test_get_seed_vector_case_insensitive():
    genes = ["apoe","trem2"]
    vec = get_seed_vector(genes)
    assert abs(vec.sum() - 1.0) < 1e-9
