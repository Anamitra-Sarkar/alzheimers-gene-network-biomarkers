"""Tests for STRING protein.info parser -> gene symbol mapping."""

import gzip
import pytest

from data_pipeline.string_info import parse_string_info, translate_gene_list


def _write_info(tmp_path, content: str, gz: bool = False):
    p = tmp_path / ("info.txt.gz" if gz else "info.txt")
    if gz:
        with gzip.open(p, "wt") as f:
            f.write(content)
    else:
        p.write_text(content)
    return p


def test_parse_info_basic(tmp_path):
    content = "#string_protein_id\tpreferred_name\n9606.ENSP000001\tAPOE\n9606.ENSP000002\tTREM2\n9606.ENSP000003\tBIN1\n"
    p = _write_info(tmp_path, content)
    m = parse_string_info(p)
    assert m["9606.ENSP000001"] == "APOE"
    assert len(m) == 3


def test_parse_info_gz(tmp_path):
    content = "#string_protein_id\tpreferred_name\n9606.ENSP001\tAPOE\n9606.ENSP002\tTREM2\n"
    p = _write_info(tmp_path, content, gz=True)
    m = parse_string_info(p)
    assert len(m) == 2


def test_parse_info_tab_and_extra_columns(tmp_path):
    content = "#string_protein_id\tpreferred_name\tprotein_size\tannotation\n9606.ENSP001\tAPOE\t123\tfoo\n9606.ENSP002\tTREM2\t456\tbar\n"
    p = _write_info(tmp_path, content)
    m = parse_string_info(p)
    assert m["9606.ENSP001"] == "APOE"


def test_parse_info_space_separated_fallback(tmp_path):
    content = "#string_protein_id preferred_name\n9606.ENSP001 APOE\n9606.ENSP002 TREM2\n"
    p = _write_info(tmp_path, content)
    m = parse_string_info(p)
    assert len(m) == 2


def test_parse_info_with_comments_and_empty_lines(tmp_path):
    content = "#string_protein_id\tpreferred_name\n9606.ENSP001\tAPOE\n# comment\n\n9606.ENSP002\tTREM2\n"
    p = _write_info(tmp_path, content)
    m = parse_string_info(p)
    assert len(m) == 2


def test_parse_info_header_only_returns_empty(tmp_path):
    content = "#string_protein_id\tpreferred_name\n"
    p = _write_info(tmp_path, content)
    m = parse_string_info(p)
    assert m == {}


def test_parse_info_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        parse_string_info(tmp_path / "nonexistent.txt")


def test_parse_info_without_hash_header(tmp_path):
    # some files may have header without leading '#'
    content = "string_protein_id\tpreferred_name\n9606.ENSP001\tAPOE\n9606.ENSP002\tTREM2\n"
    p = _write_info(tmp_path, content)
    m = parse_string_info(p)
    assert len(m) == 2


def test_translate_gene_list_basic():
    proteins = ["9606.ENSP001", "9606.ENSP002", "9606.ENSP003"]
    mapping = {"9606.ENSP001": "APOE", "9606.ENSP002": "TREM2"}
    out = translate_gene_list(proteins, mapping)
    assert out == ["APOE", "TREM2", "9606.ENSP003"]  # fallback raw ID


def test_translate_gene_list_all_mapped():
    proteins = ["9606.ENSP001", "9606.ENSP002"]
    mapping = {"9606.ENSP001": "APOE", "9606.ENSP002": "TREM2"}
    out = translate_gene_list(proteins, mapping)
    assert out == ["APOE", "TREM2"]


def test_translate_empty():
    assert translate_gene_list([], {}) == []
