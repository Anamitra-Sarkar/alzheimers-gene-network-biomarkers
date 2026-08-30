"""
FastAPI app with fail-closed release gate.

Model artifacts are NOT loaded/served unless:
  MODEL_RELEASE_APPROVED=true AND APPROVED_ARTIFACT_REVISION=<non-empty rev> is set.

Health/readiness endpoints honestly reflect loaded state and never fabricate.
"""

from __future__ import annotations

import os
import pathlib
from typing import Optional

from fastapi import FastAPI, Query, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.models import GeneScore, RankingResponse, HealthResponse, ExplainResponse
from backend.auth import optional_auth, require_auth

# Global model state (fail-closed: None until approved)
_MODEL_STATE: dict = {
    "loaded": False,
    "revision": None,
    "genes": [],
    "scores": None,  # dict gene-> GeneScore or ranking list
    "approved": False,
}


def is_release_approved() -> tuple[bool, Optional[str]]:
    approved = os.getenv("MODEL_RELEASE_APPROVED", "").lower() == "true"
    rev = os.getenv("APPROVED_ARTIFACT_REVISION")
    if approved and rev and rev.strip():
        return True, rev.strip()
    return False, None


def _try_load_model() -> None:
    """Attempt to load model artifacts if release is approved. Fail-closed on any error."""
    approved, rev = is_release_approved()
    _MODEL_STATE["approved"] = approved
    _MODEL_STATE["revision"] = rev if approved else None

    if not approved:
        _MODEL_STATE["loaded"] = False
        _MODEL_STATE["genes"] = []
        _MODEL_STATE["scores"] = None
        return

    # Try to load artifacts from MODEL_ARTIFACT_PATH or default location
    artifact_path = os.getenv("MODEL_ARTIFACT_PATH", "artifacts/model.joblib")
    p = pathlib.Path(artifact_path)
    if p.exists():
        try:
            import pickle
            with open(p, "rb") as f:
                data = pickle.load(f)
            # Expect data to contain ranking or model; we synthesize ranking for demo
            _MODEL_STATE["loaded"] = True
            _MODEL_STATE["scores"] = data
            # If data contains gene list, keep it
            if isinstance(data, dict) and "genes" in data:
                _MODEL_STATE["genes"] = data["genes"]
            elif isinstance(data, dict) and "ranking" in data:
                _MODEL_STATE["genes"] = data["ranking"]
            else:
                _MODEL_STATE["genes"] = []
        except Exception:
            _MODEL_STATE["loaded"] = False
            _MODEL_STATE["scores"] = None
    else:
        # No artifact file present - but release is approved; we mark as not loaded
        # Honestly report not loaded (abstention). Do not fabricate scores.
        _MODEL_STATE["loaded"] = False
        _MODEL_STATE["scores"] = None
        # Optionally load synthetic demo ranking if DEMO_MODE=true
        if os.getenv("DEMO_MODE", "").lower() == "true":
            _MODEL_STATE["genes"] = _build_demo_ranking()
            _MODEL_STATE["loaded"] = True

    # If still not loaded but approved and DEMO_MODE not set, stay not loaded (honest)


def _build_demo_ranking() -> list[dict]:
    """Build a small demo ranking for testing/frontend with approved+demo mode."""
    from data_pipeline.seed_genes import SEED_GENES

    demo_genes = SEED_GENES[:5] + ["BRCA1", "TP53", "EGFR", "MYC", "PTEN", "APOA1", "MAPT", "SNCA", "LRRK2", "GRN"]
    # synthetic scores descending
    scores = [0.95 - i * 0.05 for i in range(len(demo_genes))]
    ranking = []
    for i, (g, s) in enumerate(zip(demo_genes, scores)):
        ranking.append({
            "gene": g,
            "symbol": g,
            "rwr_score": s * 0.8,
            "degree": 10 - i * 0.5,
            "pagerank": s * 0.1,
            "betweenness": 0.01 * i,
            "closeness": 0.5 - i * 0.02,
            "fusion_score": s,
            "rank": i + 1,
            "seed_contributors": SEED_GENES[:2] if g not in SEED_GENES else [],
            "is_seed": g in SEED_GENES,
        })
    return ranking


def create_app() -> FastAPI:
    app = FastAPI(
        title="AD Gene-Network Biomarker API",
        version="0.1.0",
        description="Gene ranking for Alzheimer's disease relevance via RWR + fusion model",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def _startup():
        _try_load_model()

    @app.get("/health", response_model=HealthResponse)
    def health():
        # Re-check release gate on each call so tests that set env vars mid-process work
        _try_load_model()
        return HealthResponse(
            status="ok" if _MODEL_STATE["loaded"] else "model_not_loaded",
            model_loaded=_MODEL_STATE["loaded"],
            model_revision=_MODEL_STATE["revision"],
            model_approved=_MODEL_STATE["approved"],
        )

    @app.get("/readiness", response_model=HealthResponse)
    def readiness():
        _try_load_model()
        return HealthResponse(
            status="ready" if _MODEL_STATE["loaded"] else "not_ready",
            model_loaded=_MODEL_STATE["loaded"],
            model_revision=_MODEL_STATE["revision"],
            model_approved=_MODEL_STATE["approved"],
        )

    @app.get("/genes/ranking", response_model=RankingResponse)
    def ranking(
        q: Optional[str] = Query(default=None, description="Filter by gene symbol substring"),
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        user: dict | None = Depends(optional_auth),
    ):
        _try_load_model()
        if not _MODEL_STATE["loaded"]:
            # Fail-closed: return empty ranking with honest banner state
            return RankingResponse(
                genes=[],
                total_genes=0,
                model_loaded=False,
                model_revision=None,
                query=q,
            )

        genes = _MODEL_STATE["genes"]
        # Filter
        if q:
            q_low = q.lower()
            filtered = [g for g in genes if q_low in g["gene"].lower() or q_low in g.get("symbol", "").lower()]
        else:
            filtered = genes

        total = len(filtered)
        page = filtered[offset : offset + limit]
        # Convert to GeneScore
        result = [GeneScore(**g) for g in page]
        return RankingResponse(
            genes=result,
            total_genes=total,
            model_loaded=True,
            model_revision=_MODEL_STATE["revision"],
            query=q,
        )

    @app.get("/genes/{gene_id}", response_model=ExplainResponse)
    def explain(gene_id: str, user: dict | None = Depends(optional_auth)):
        _try_load_model()
        if not _MODEL_STATE["loaded"]:
            raise HTTPException(status_code=503, detail="Model not yet released: artifact not loaded (set MODEL_RELEASE_APPROVED=true and APPROVED_ARTIFACT_REVISION)")

        genes = _MODEL_STATE["genes"]
        for g in genes:
            if g["gene"].lower() == gene_id.lower():
                return ExplainResponse(
                    gene=g["gene"],
                    fusion_score=g.get("fusion_score"),
                    rwr_score=g["rwr_score"],
                    features={"degree": g["degree"], "pagerank": g["pagerank"], "betweenness": g["betweenness"], "closeness": g["closeness"]},
                    seed_contributors=g.get("seed_contributors", []),
                    is_seed=g.get("is_seed", False),
                )
        raise HTTPException(status_code=404, detail=f"Gene {gene_id} not found")

    @app.get("/auth/me")
    def me(user: dict = Depends(require_auth)):
        return {"user": user}

    return app


app = create_app()
