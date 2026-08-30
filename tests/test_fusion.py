import numpy as np
import pandas as pd
import pytest

from data_pipeline.fusion import (
    build_model, train_fusion_model, predict_scores,
    recall_at_k, evaluate_ranking, cross_validate, leave_one_seed_out_eval
)


def _synthetic_df(n=50, seed=42):
    rng = np.random.default_rng(seed)
    # Create features where rwr_score correlates with label
    y = np.zeros(n, dtype=int)
    # positives at indices 0..4
    y[:5] = 1
    rwr = rng.random(n) * 0.3
    rwr[:5] += 0.6  # boost positives
    degree = rng.random(n)
    degree[:5] += 0.2
    pagerank = rng.random(n) * 0.1 + rwr * 0.2
    betweenness = rng.random(n) * 0.05
    closeness = rng.random(n) * 0.5 + 0.3
    genes = [f"GENE{i}" for i in range(n)]
    df = pd.DataFrame({
        "gene": genes,
        "degree": degree*10,
        "degree_norm": degree,
        "pagerank": pagerank,
        "betweenness": betweenness,
        "closeness": closeness,
        "rwr_score": rwr,
    })
    return df, y


def test_recall_at_k():
    y_true = np.array([1,1,0,0,0,0,0,1])
    # Rank: index 0 score 0.9 (hit), 1 0.8 (hit), 7 0.1 (miss if k=2)
    y_score = np.array([0.9,0.8,0.7,0.6,0.5,0.4,0.3,0.1])
    assert recall_at_k(y_true, y_score, k=2) == pytest.approx(2/3)
    assert recall_at_k(y_true, y_score, k=10) == pytest.approx(1.0)
    assert recall_at_k(np.zeros(5), np.ones(5), k=2) == 0.0


def test_train_and_predict():
    df, y = _synthetic_df()
    feature_cols = ["rwr_score","degree_norm","pagerank","betweenness","closeness"]
    model = train_fusion_model(df[feature_cols], y, model_type="logistic")
    scores = predict_scores(model, df[feature_cols])
    assert len(scores) == len(y)
    assert (scores >= 0).all() and (scores <= 1).all()
    # positives should on average score higher than negatives
    assert scores[y==1].mean() > scores[y==0].mean()


def test_build_model_gbt():
    df, y = _synthetic_df()
    model = train_fusion_model(df[["rwr_score","degree_norm"]], y, model_type="gbt")
    scores = predict_scores(model, df[["rwr_score","degree_norm"]])
    assert len(scores) == len(y)


def test_evaluate_ranking():
    df, y = _synthetic_df(n=30)
    feature_cols = ["rwr_score","degree_norm","pagerank"]
    model = train_fusion_model(df[feature_cols], y)
    scores = predict_scores(model, df[feature_cols])
    baseline = df["degree_norm"].values
    result = evaluate_ranking(y, scores, baseline)
    assert "recall_at_k" in result.__dict__ or hasattr(result, "recall_at_k")
    assert 10 in result.recall_at_k
    assert 0 <= result.auprc <= 1
    assert 0 <= result.baseline_auprc <= 1


def test_cross_validate():
    df, y = _synthetic_df(n=50)
    feature_cols = ["rwr_score","degree_norm","pagerank","betweenness","closeness"]
    result = cross_validate(df, y, feature_cols, baseline_col="degree_norm", cv=5)
    assert result.auprc > 0
    # fusion should generally beat degree baseline on this synthetic where rwr is informative
    # (not guaranteed every random seed, but with our construction it should)
    assert result.auprc >= result.baseline_auprc - 0.1


def test_leave_one_seed_out():
    df, y = _synthetic_df(n=30)
    feature_cols = ["rwr_score","degree_norm","pagerank"]
    result = leave_one_seed_out_eval(df, y, feature_cols)
    assert 10 in result.recall_at_k
    assert 0 <= result.auprc <= 1
