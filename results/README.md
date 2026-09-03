# Real training run — STRING v12 (2026-09-03)

First real (non-synthetic) run of this repository's own pipeline
(`data_pipeline.real_run.run`), executed on Modal CPU. Raw output:
`real-run-string-v12-metrics.json`. Reproduce with `scripts_real_run_modal.py`.

## Data — real, public, no auth

| Input | Source | Size |
|---|---|---|
| PPI edges | `https://stringdb-downloads.org/download/protein.links.v12.0/9606.protein.links.v12.0.txt.gz` | 83,164,437 bytes |
| ID → symbol | `https://stringdb-downloads.org/download/protein.info.v12.0/9606.protein.info.v12.0.txt.gz` | 1,970,090 bytes |

Confidence threshold 700, as the README specifies.

- **16,201 proteins, 473,860 edges** after thresholding.
- **16,201/16,201** STRING protein IDs translated to gene symbols.
- **26/26** AD GWAS seed genes present in the graph. The pipeline aborts if fewer
  than 5 survive translation, so this is a checked result, not an assumed one.

## Result — leakage-free leave-one-seed-out CV

Features: `degree_norm`, `pagerank`, `betweenness` (k=200 approx.), `closeness`,
`rwr_score`. Model: logistic fusion.

| Model | Recall@10 | Recall@25 | Recall@50 | Recall@100 | AUPRC |
|---|---|---|---|---|---|
| **Fusion (RWR + topology)** | 0.346 | 0.692 | 0.769 | 0.769 | **0.654** |
| Degree-only baseline | 0.000 | 0.000 | 0.000 | 0.000 | 0.004 |

The evaluation is leave-one-seed-out and **leakage-free**: for each held-out seed
gene the RWR is re-run without that gene in the restart vector, so its own
propagation signal cannot leak into its score. Without that precaution an RWR
feature trivially recovers its own seeds and the number is meaningless.

## Honest reading

The degree-only baseline scoring ~0 recall is the informative part: hub-ness alone
does not find AD genes in this graph, so the fusion result is not a popularity
artifact. AUPRC 0.654 against a 26-positive / 16,201-gene set (positive rate
~0.16%) is a real signal.

Recall@10 of 0.346 means roughly a third of held-out AD seeds surface in the top
10 of ~16k genes. Recall plateaus between k=50 and k=100 — the remaining ~23% of
seeds are not recovered by network topology at all, which is expected for genes
whose AD association is driven by mechanisms this PPI graph does not encode
(e.g. `HLA-DRB1`'s immune context, or expression-level effects).

This is a **gene prioritisation / hypothesis generation** result on a static PPI
network. It is not a diagnostic, and it does not establish causality.
