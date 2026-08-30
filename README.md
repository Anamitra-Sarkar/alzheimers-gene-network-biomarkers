# Alzheimer's Gene-Network Biomarker Discovery

Gene-network learning that scores all human genes for Alzheimer's disease relevance by **Random Walk with Restart (RWR)** over the STRING PPI network (human 9606, confidence ≥700) seeded from 26 established AD GWAS loci, fused with topology features (degree, PageRank, betweenness, harmonic closeness) via an honest logistic/GBT ranking pipeline.

- **Real data endpoints:** STRING `https://stringdb-downloads.org/download/protein.links.v12.0/9606.protein.links.v12.0.txt.gz` + API `https://string-db.org/api/`, GEO optional `GSE5281` / `GSE118553`.
- **Evaluation:** leave-one-seed-out / k-fold CV, **recall@k (10,25,50,100) + AUPRC** vs degree-only baseline.
- **Safety:** backend is fail-closed — `MODEL_RELEASE_APPROVED=true` + `APPROVED_ARTIFACT_REVISION` required to serve rankings; health endpoints honestly report loaded state. Firebase-auth-shaped bearer verification stub included.

## Quick start

```bash
pip install -r requirements.txt
pytest -q
```

## Real run (Kaggle/Modal)

```bash
wget https://stringdb-downloads.org/download/protein.links.v12.0/9606.protein.links.v12.0.txt.gz
python -m data_pipeline.cli build-graph --string-path 9606.protein.links.v12.0.txt.gz --output artifacts/graph --threshold 700
python -m data_pipeline.cli run-rwr --graph artifacts/graph.npz --output artifacts/rwr.npy --restart 0.3
# build features DataFrame (see docs/architecture.md), then:
python -m data_pipeline.cli train --features artifacts/features.parquet --output artifacts/model.joblib
MODEL_RELEASE_APPROVED=true APPROVED_ARTIFACT_REVISION=$(git rev-parse HEAD) uvicorn backend.app:app --port 8000
```

## Frontend

```bash
cd frontend && npm install && npm run dev
# or build: npm run build
```

## Structure

- `data_pipeline/` — STRING parser, seed genes, RWR, features, fusion + eval, CLI
- `backend/` — FastAPI with release gate + auth stub
- `frontend/` — React/Vite/TS (gene search, ranked table, explanation drawer, abstention banner)
- `tests/` — pytest with 10-50 node synthetic fixtures (RWR convergence, features, fusion recall@k/AUPRC, release gate)
- `docs/architecture.md` / `docs/data_sources.md` — real endpoints and citations
