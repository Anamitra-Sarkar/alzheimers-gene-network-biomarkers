# Architecture — AD Gene-Network Biomarker Discovery

## Overview

This system scores all human genes for Alzheimer's disease relevance by **network propagation** over the STRING PPI graph seeded from known AD GWAS loci, fused with topology features into an honest, evaluated ranking.

```
STRING PPI (confidence >=700)  ──┐
                                ├─► RWR (sparse, restart 0.3) ─► rwr_score
Known AD seed genes (26 loci) ──┘           │
                                            ▼
                              degree / PageRank / betweenness / closeness
                                            │
                                            ▼
                                    Fusion model (logistic / GBT)
                                            │
                                            ▼
                                   Ranked gene list + explanations
                                            │
                              ┌─────────────┴──────────────┐
                              │ FastAPI (release-gated)    │
                              │ React/Vite frontend        │
                              └────────────────────────────┘
```

## Components

### 1. `data_pipeline/string_parser.py`
- Parser for `9606.protein.links.v12.0.txt(.gz)` — header `protein1 protein2 combined_score`.
- Filters `combined_score >= 700` (high-confidence). Documented real endpoints: `https://stringdb-downloads.org/download/protein.links.v12.0/9606.protein.links.v12.0.txt.gz` and API `https://string-db.org/api/`.
- Builds symmetric sparse adjacency (`scipy.sparse.csr_matrix`) and column-normalized transition matrix `W = A D^{-1}`.
- Real run: `python -m data_pipeline.cli build-graph --string-path <local file> --output artifacts/graph --threshold 700`. No download occurs in CI/sandbox.

### 2. `data_pipeline/seed_genes.py`
- 26 hard-coded seed genes: APOE, APP, PSEN1, PSEN2, TREM2, CLU, CR1, PICALM, BIN1, ABCA7, SORL1, CD33, MS4A6A, ADAM10, PLCG2, CD2AP, EPHA1, HLA-DRB1, MEF2C, INPP5D, FERMT2, CELF1, NME8, CASS4, SPI1, ACE.
- Sources: Lambert 2013, Kunkle 2019, Bellenguez 2022, plus Mendelian genes. Citations in `docs/data_sources.md`.
- `get_seed_vector()` produces uniform `p0` over seeds present in graph (sum=1).

### 3. `data_pipeline/rwr.py`
- Sparse RWR: `p_{t+1} = (1-r) W p_t + r p_0`, `r=0.3` (configurable 0.15–0.3). Uses CSC for fast column ops.
- Converges when L1 delta < 1e-6 or max 100 iters. Normalizes final `p` to sum=1. Handles dangling nodes (leaked mass re-normalized honestly).
- Returns per-gene steady-state scores; higher = closer in network to AD seed manifold.

### 4. `data_pipeline/features.py`
- Per-gene features: degree, degree_norm, PageRank (power iteration, α=0.85), betweenness (exact for n<=500 else k-sample min(100,n) approximation — documented tradeoff), harmonic/closeness centrality (harmonic better for disconnected graphs).
- Uses NetworkX on the undirected graph derived from the sparse adjacency.
- Optional: caller passes `rwr_scores` to include as an additional column (`rwr_score`) for fusion.

### 5. `data_pipeline/fusion.py`
- Fusion layer: `StandardScaler` + Logistic Regression (balanced, lbfgs) or Gradient-Boosted Trees. Prefers simple defensible models.
- Features = RWR + topology (4–5 columns). Trained on labels where positives = known AD seeds (or held-in seeds during CV).
- Evaluation: k-fold CV or leave-one-seed-out, reporting **recall@k** (k=10,25,50,100) and **AUPRC** vs degree-only baseline. Mirrors sibling project protocol.
- `cross_validate()` and `leave_one_seed_out_eval()` aggregate out-of-fold scores forRanking evaluation.

### 6. `backend/app.py` — Release Gate
- Fail-closed pattern: model artifacts are **not loaded** unless `MODEL_RELEASE_APPROVED=true` and `APPROVED_ARTIFACT_REVISION` is non-empty.
- `GET /health` and `GET /readiness` honestly report `model_loaded`, `model_approved`, `model_revision`. Never fabricate loaded state.
- `GET /genes/ranking` returns `[]` with `model_loaded:false` when not released (honest abstention). `GET /genes/{id}` returns 503 when not loaded.
- Optional `DEMO_MODE=true` allows approved-release tests to synthesize a demo ranking without a real artifact file.
- Auth: Firebase-shaped stub (`backend/auth.py`) reading `FIREBASE_SERVICE_ACCOUNT_JSON`; `verify_bearer_token` accepts mocked verifier. `GET /auth/me` requires valid Bearer token (401 otherwise).

### 7. Frontend — React + Vite + TypeScript
- No default Vite boilerplate styling. Clean modern layout: header with model status badge, abstention banner when not released, search box, ranked table, detail drawer with seed contributors, footer with data citations.
- Banner matches backend's release gate honestly (`model not yet released` vs `Model loaded rev …`).
- Table shows rank, gene, fusion, RWR, PageRank, degree, explain; seed genes highlighted; clicking opens explanation pane (which seed genes drove the score).
- Types in `src/App.tsx`; components `Banner`, `SearchBox`, `GeneTable`.

## Real-Run Procedure (Kaggle/Modal)

```bash
# 1. Download STRING
wget https://stringdb-downloads.org/download/protein.links.v12.0/9606.protein.links.v12.0.txt.gz
# 2. Build graph
python -m data_pipeline.cli build-graph --string-path 9606.protein.links.v12.0.txt.gz --output artifacts/graph --threshold 700
# 3. Run RWR (uses seed genes inside)
python -m data_pipeline.cli run-rwr --graph artifacts/graph.npz --output artifacts/rwr.npy --restart 0.3
# 4. Compute features + train (features need to include rwr + topology)
#    (construct features DataFrame via data_pipeline.features.compute_features + add labels)
python -m data_pipeline.cli train --features artifacts/features.parquet --output artifacts/model.joblib --model-type logistic
# 5. Serve
MODEL_RELEASE_APPROVED=true APPROVED_ARTIFACT_REVISION=$(git rev-parse HEAD) MODEL_ARTIFACT_PATH=artifacts/model.joblib uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

GEO differential-expression (optional, not required for ranking) would use GSE5281 or GSE118553; not implemented in this iteration but documented in `data_sources.md`.

## Tradeoffs Documented
- Betweenness exact O(n·m) — approximated via k-sample for n>500.
- AUPRC/recall computed on synthetic fixtures in tests; real STRING scale (19k nodes, high-confidence edges ~ couple hundred k) is intended for real runs, not CI.
- Closeness uses harmonic centrality to handle disconnected STRING components.
