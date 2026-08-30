"""
Fusion model combining RWR + topology features.

We provide a simple, defensible model (logistic regression or gradient-boosted trees)
rather than an overcomplicated deep model. Supports:
 - training on labeled genes (1 = AD known, 0 = rest)
 - leave-one-seed-out / k-fold CV evaluation
 - metrics: recall@k (k=10,25,50,100), AUPRC, compared to degree-only baseline
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold, KFold
from sklearn.metrics import average_precision_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline


ModelType = Literal["logistic", "gbt"]


@dataclass
class EvalResult:
    recall_at_k: dict[int, float]
    auprc: float
    baseline_recall_at_k: dict[int, float]
    baseline_auprc: float
    y_true: np.ndarray
    y_score: np.ndarray
    baseline_score: np.ndarray


def build_model(model_type: ModelType = "logistic") -> Pipeline:
    """Build sklearn pipeline with StandardScaler + classifier."""
    if model_type == "logistic":
        clf = LogisticRegression(max_iter=1000, class_weight="balanced", solver="lbfgs")
    elif model_type == "gbt":
        clf = GradientBoostingClassifier(random_state=42)
    else:
        raise ValueError(f"Unknown model_type {model_type}")
    return Pipeline([("scaler", StandardScaler()), ("clf", clf)])


def train_fusion_model(
    X: pd.DataFrame | np.ndarray,
    y: np.ndarray,
    model_type: ModelType = "logistic",
) -> Pipeline:
    """Train fusion model on feature matrix X and labels y."""
    if isinstance(X, pd.DataFrame):
        # drop non-numeric / gene column if present
        X_vals = X.select_dtypes(include=[np.number]).values
    else:
        X_vals = X
    model = build_model(model_type)
    model.fit(X_vals, y)
    return model


def predict_scores(model: Pipeline, X: pd.DataFrame | np.ndarray) -> np.ndarray:
    """Return positive-class probability scores."""
    if isinstance(X, pd.DataFrame):
        X_vals = X.select_dtypes(include=[np.number]).values
    else:
        X_vals = X
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X_vals)[:, 1]
    return model.decision_function(X_vals)


def recall_at_k(y_true: np.ndarray, y_score: np.ndarray, k: int) -> float:
    """
    Recall@k: fraction of positives ranked in top-k by score.
    If k >= n, returns 1.0 if all positives found.
    """
    n = len(y_true)
    k = min(k, n)
    if y_true.sum() == 0:
        return 0.0
    # argsort descending
    order = np.argsort(y_score)[::-1]
    top_k_idx = order[:k]
    hits = y_true[top_k_idx].sum()
    return float(hits / y_true.sum())


def evaluate_ranking(
    y_true: np.ndarray,
    y_score: np.ndarray,
    baseline_score: np.ndarray,
    ks: list[int] | tuple[int, ...] = (10, 25, 50, 100),
) -> EvalResult:
    """Compute recall@k and AUPRC for model and baseline."""
    # AUPRC
    if y_true.sum() == 0 or y_true.sum() == len(y_true):
        auprc = float("nan")
        baseline_auprc = float("nan")
    else:
        auprc = float(average_precision_score(y_true, y_score))
        baseline_auprc = float(average_precision_score(y_true, baseline_score))

    recall = {k: recall_at_k(y_true, y_score, k) for k in ks}
    baseline_recall = {k: recall_at_k(y_true, baseline_score, k) for k in ks}

    return EvalResult(
        recall_at_k=recall,
        auprc=auprc,
        baseline_recall_at_k=baseline_recall,
        baseline_auprc=baseline_auprc,
        y_true=y_true,
        y_score=y_score,
        baseline_score=baseline_score,
    )


def cross_validate(
    df: pd.DataFrame,
    labels: np.ndarray,
    feature_cols: list[str],
    baseline_col: str = "degree_norm",
    model_type: ModelType = "logistic",
    cv: int = 5,
    ks: tuple[int, ...] = (10, 25, 50, 100),
) -> EvalResult:
    """
    K-fold CV over labeled genes. Trains fusion model on each fold and aggregates
    out-of-fold predictions for ranking evaluation.

    For leave-one-seed-out, caller can set cv = number_of_positives and use
    appropriate splitter manually; this function provides standard k-fold.
    """
    X = df[feature_cols].values
    baseline = df[baseline_col].values if baseline_col in df.columns else df["degree_norm"].values

    n = len(labels)
    # Choose splitter: Stratified if both classes have enough members
    n_pos = int(labels.sum())
    n_neg = n - n_pos
    if n_pos >= cv and n_neg >= cv:
        splitter = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)
        splits = splitter.split(X, labels)
    else:
        splitter = KFold(n_splits=min(cv, n), shuffle=True, random_state=42)
        splits = splitter.split(X)

    oof_scores = np.zeros(n, dtype=float)

    for train_idx, test_idx in splits:
        model = build_model(model_type)
        model.fit(X[train_idx], labels[train_idx])
        proba = model.predict_proba(X[test_idx])[:, 1]
        oof_scores[test_idx] = proba

    return evaluate_ranking(labels, oof_scores, baseline, ks=list(ks))


def leave_one_seed_out_eval(
    df: pd.DataFrame,
    labels: np.ndarray,
    feature_cols: list[str],
    baseline_col: str = "degree_norm",
    model_type: ModelType = "logistic",
) -> EvalResult:
    """
    Leave-one-positive-out CV: each positive sample is held out once, model trained
    on remaining data. Aggregates scores for held-out positives + sampled negatives.
    For synthetic/small graphs we do full LOPO over positives but score all genes
    ranking each fold: here we aggregate OOF across all samples for simplicity.
    """
    X = df[feature_cols].values
    baseline = df[baseline_col].values if baseline_col in df.columns else df["degree_norm"].values
    n = len(labels)
    pos_idx = np.where(labels == 1)[0]
    neg_idx = np.where(labels == 0)[0]

    oof_scores = np.zeros(n, dtype=float)

    # For each positive held out, train on rest, predict held-out positive + all negatives predicted from last model
    # Simpler: do KFold where k = n_pos (if n_pos <= 20 and feasible)
    # We implement: for each pos, train on all except that pos, predict all samples (but only OOF for the held-out)
    # For negatives, we average predictions across folds.
    neg_scores_accum = np.zeros(len(neg_idx))
    # To give negatives a score, average over folds
    for p in pos_idx:
        train_mask = np.ones(n, dtype=bool)
        train_mask[p] = False
        model = build_model(model_type)
        model.fit(X[train_mask], labels[train_mask])
        # score held-out positive
        oof_scores[p] = model.predict_proba(X[p : p + 1])[0, 1]
        # accumulate neg scores
        neg_scores_accum += model.predict_proba(X[neg_idx])[:, 1]

    if len(pos_idx) > 0:
        neg_scores_accum /= len(pos_idx)
        oof_scores[neg_idx] = neg_scores_accum

    return evaluate_ranking(labels, oof_scores, baseline, ks=[10, 25, 50, 100])
