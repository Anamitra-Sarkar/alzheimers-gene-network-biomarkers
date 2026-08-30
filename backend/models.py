"""Pydantic models for API."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class GeneScore(BaseModel):
    gene: str
    symbol: str
    rwr_score: float
    degree: float
    pagerank: float
    betweenness: float
    closeness: float
    fusion_score: Optional[float] = None
    rank: int
    seed_contributors: list[str] = Field(default_factory=list, description="Seed genes with highest RWR path influence; empty if model not loaded")
    is_seed: bool = False


class RankingResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    genes: list[GeneScore]
    total_genes: int
    model_loaded: bool
    model_revision: Optional[str] = None
    query: Optional[str] = None


class HealthResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    status: str
    model_loaded: bool
    model_revision: Optional[str] = None
    model_approved: bool


class ExplainResponse(BaseModel):
    gene: str
    fusion_score: Optional[float]
    rwr_score: float
    features: dict
    seed_contributors: list[str]
    is_seed: bool
