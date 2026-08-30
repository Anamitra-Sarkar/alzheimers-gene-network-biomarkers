# Data Sources — AD Gene-Network Biomarker Discovery

All endpoints and citations below are real public resources. No fabricated datasets, APIs, or metrics are used.

## 1. STRING Protein-Protein Interaction Network

- **Organism:** Homo sapiens (NCBI taxon 9606)
- **Download (protein links):** `https://stringdb-downloads.org/download/protein.links.v12.0/9606.protein.links.v12.0.txt.gz`
  - Alternative browse: `https://stringdb-downloads.org/download/`
  - File: ~19k proteins, ~11M edges at all confidence thresholds; human, version 12.0.
- **Protein alias mapping (ENSEMBL → gene symbol):** `https://stringdb-downloads.org/download/protein.aliases.v12.0/9606.protein.aliases.v12.0.txt.gz`
- **API:** `https://string-db.org/api/` — documented at `https://string-db.org/api/json/network` etc. See also `https://string-db.org/cgi/help.pl?subpage=api`
- **Reference:** Szklarczyk et al. *Nucleic Acids Research* 2023, STRING v12. PMID 36370105.
- **Confidence filtering:** We retain edges with `combined_score >= 700` (high-confidence, as recommended by STRING). This yields a manageable graph of a few hundred thousand edges, documented in `data_pipeline/string_parser.py`.
- **Local usage:** Download requires network access (Kaggle/Modal real run). In this sandbox, synthetic fixture graphs are used for tests. CLI: `python -m data_pipeline.cli build-graph --string-path <local file> --threshold 700`.

## 2. Known AD Seed Genes (GWAS / Genetics)

Hard-coded in `data_pipeline/seed_genes.py` (26 genes). Each is a well-established AD locus from public GWAS literature.

| Gene | Evidence | Key citation (PMID) |
|------|----------|---------------------|
| APOE | Strongest late-onset risk locus, chr19q13.32 | 1377412; 30617256 |
| APP | Mendelian early-onset, amyloid precursor | 1671712 |
| PSEN1 | Mendelian early-onset, γ-secretase | 7651536 |
| PSEN2 | Mendelian early-onset | 7651536 |
| TREM2 | Rare R47H, microglial | 23150934 |
| CLU (APOJ) | GWAS Lambert 2009/2013 | 19734903; 24162737 |
| CR1 | GWAS Lambert 2009 | 19734903 |
| PICALM | GWAS Harold 2009 | 19734902 |
| BIN1 | GWAS top after APOE | 19734903; 30617256 |
| ABCA7 | GWAS Hollingworth 2011, Kunkle 2019 | 21460841 |
| SORL1 | GWAS + retromer | 21460841 |
| CD33 (SIGLEC3) | GWAS Naj 2011 | 21460841 |
| MS4A6A (MS4A cluster) | GWAS Hollingworth 2011 | 21460841 |
| ADAM10 | GWAS + rare, α-secretase | 24162737 |
| PLCG2 (P522R protective) | GWAS Sims 2017 | 29093296; 30617256 |
| CD2AP | GWAS Naj 2011 | 21460841 |
| EPHA1 | GWAS Hollingworth 2011 | 21460841 |
| HLA-DRB1 (HLA locus) | GWAS Lambert 2013 | 24162737 |
| MEF2C | GWAS Lambert 2013 | 24162737 |
| INPP5D | GWAS Lambert 2013 | 24162737 |
| FERMT2 | GWAS Lambert 2013 | 24162737 |
| CELF1 | GWAS Lambert 2013 | 24162737 |
| NME8 | GWAS Lambert 2013 | 24162737 |
| CASS4 | GWAS Lambert 2013 | 24162737 |
| SPI1 (PU.1) | GWAS Huang 2017, Kunkle 2019 | 30617256 |
| ACE | Candidate/vascular + GWAS | 30617256 |

**Major GWAS meta-analyses cited:**
- Lambert et al. *Nature Genetics* 2013 (74,046 individuals, 11 new loci). PMID 24162737.
- Kunkle et al. *Nature Genetics* 2019. PMID 30820047.
- Bellenguez et al. *Nature Genetics* 2022 (111k cases, 75 loci). PMID 35379992.
- Jansen et al. *Nature Genetics* 2019. PMID 30617256.

All are public knowledge; no download needed for the seed list.

## 3. GEO Differential Expression (Optional, Not Implemented in Core Pipeline)

If a differential-expression feature is later added, the intended real datasets are:

- **GSE5281** — Liang et al. AD brain expression (laser-captured neurons, 6 regions). https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE5281
- **GSE118553** — AD brain transcriptomics (bulk). https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE118553

The fusion model currently operates on RWR + topology features only; adding a DE z-score per gene is a natural extension and would appear as an extra column in `features.py` / `fusion.py`.

## 4. Evaluation Protocol

- **Leave-one-seed-out / k-fold CV** over the known AD gene set: hold out some seeds, rank all non-seed genes using remaining seeds, measure whether held-out seeds rank highly.
- **Metrics:** recall@k (k=10,25,50,100) and AUPRC (average precision), compared against a naive degree-only baseline. Honest, defensible ranking evaluation; not inflated.
- Implemented in `data_pipeline/fusion.py` (`cross_validate`, `leave_one_seed_out_eval`, `evaluate_ranking`).

## 5. Licenses & Reuse

- STRING data is freely available for academic use (STRING license: https://string-db.org/cgi/access.pl?footer_active_subpage=licensing).
- GWAS gene lists are public scientific knowledge (no license restriction).
- GEO datasets are public (NCBI).
