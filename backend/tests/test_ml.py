"""Tests for ML scorer, dataset generation, and model inference."""

import pytest
import os


ML_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml")
MODEL_PATH = os.path.join(ML_DIR, "model.joblib")
METRICS_PATH = os.path.join(ML_DIR, "metrics.json")
DATASET_PATH = os.path.join(ML_DIR, "dataset.csv")


# ─── Dataset generation tests ─────────────────────────────────────────────────

def test_generate_dataset_produces_rows():
    from ml.generate_dataset import generate
    rows = generate(50)
    assert len(rows) == 50


def test_generate_dataset_has_correct_columns():
    from ml.generate_dataset import generate
    from ml.feature_config import FEATURE_NAMES
    rows = generate(10)
    for name in FEATURE_NAMES:
        assert name in rows[0], f"Missing feature column: {name}"
    assert "label" in rows[0]
    assert "risk_score" in rows[0]


def test_generate_dataset_labels_binary():
    from ml.generate_dataset import generate
    rows = generate(100)
    labels = {r["label"] for r in rows}
    assert labels.issubset({0, 1}), "Labels must be 0 or 1"


def test_generate_dataset_features_in_range():
    from ml.generate_dataset import generate
    rows = generate(50)
    for row in rows:
        assert 0.0 <= row["carrier_late_rate"] <= 1.0
        assert 0.0 <= row["mode_risk"] <= 1.0
        assert 0.0 <= row["season_risk"] <= 1.0
        assert 0.0 <= row["distance_km_norm"] <= 1.0


# ─── Feature config tests ──────────────────────────────────────────────────────

def test_feature_vector_length(sample_shipment):
    from ml.feature_config import shipment_to_features, FEATURE_NAMES
    features = shipment_to_features(sample_shipment)
    assert len(features) == len(FEATURE_NAMES)


def test_feature_vector_numeric(sample_shipment):
    from ml.feature_config import shipment_to_features
    features = shipment_to_features(sample_shipment)
    for val in features:
        assert isinstance(val, (int, float)), f"Non-numeric feature: {val}"


def test_feature_vector_finite(sample_shipment):
    import math
    from ml.feature_config import shipment_to_features
    features = shipment_to_features(sample_shipment)
    for val in features:
        assert math.isfinite(val), f"Non-finite feature value: {val}"


# ─── Model file existence ──────────────────────────────────────────────────────

def test_model_file_exists():
    assert os.path.exists(MODEL_PATH), (
        f"model.joblib not found at {MODEL_PATH}. "
        "Run: python ml/train_model.py"
    )


def test_metrics_file_exists():
    assert os.path.exists(METRICS_PATH), "metrics.json not found"


def test_metrics_content():
    import json
    with open(METRICS_PATH) as f:
        m = json.load(f)
    assert "accuracy" in m
    assert "roc_auc" in m
    assert m["accuracy"] >= 0.80, f"Accuracy too low: {m['accuracy']}"
    assert m["roc_auc"] >= 0.85, f"AUC too low: {m['roc_auc']}"


# ─── ML scorer inference tests ────────────────────────────────────────────────

def test_ml_scorer_loads(sample_shipment):
    from services.risk_scorer import MLScorer
    scorer = MLScorer()
    loaded = scorer._load()
    assert loaded, "MLScorer failed to load model.joblib"


def test_ml_scorer_returns_valid_result(sample_shipment):
    from services.risk_scorer import MLScorer
    from models.schemas import RiskLevel
    scorer = MLScorer()
    result = scorer.score(sample_shipment)
    assert result is not None, "MLScorer returned None (model load failed?)"
    assert 0 <= result.risk_score <= 100
    assert result.risk_level in list(RiskLevel)
    assert 0 <= result.confidence <= 1
    assert len(result.top_factors) >= 1


def test_ml_scorer_top_factors_sum_to_one(sample_shipment):
    from services.risk_scorer import MLScorer
    scorer = MLScorer()
    result = scorer.score(sample_shipment)
    if result:
        total = sum(f.contribution for f in result.top_factors)
        assert abs(total - 1.0) < 0.05, f"Contributions don't sum to ~1: {total}"


def test_score_shipment_prefers_ml(sample_shipment):
    """With model.joblib present, score_shipment should use ML scorer."""
    from services.risk_scorer import score_shipment, MLScorer
    if not MLScorer()._load():
        pytest.skip("ML model not available")
    result = score_shipment(sample_shipment)
    assert result is not None
    assert 0 <= result.risk_score <= 100


def test_ml_vs_rule_based_correlation(store):
    """ML and rule-based scores should be positively correlated."""
    from services.risk_scorer import MLScorer, RuleBasedScorer
    ml = MLScorer()
    rb = RuleBasedScorer()

    if not ml._load():
        pytest.skip("ML model not available")

    shipments = store.get_shipments()[:10]
    ml_scores = [ml.score(s).risk_score for s in shipments]
    rb_scores = [rb.score(s).risk_score for s in shipments]

    # Compute Pearson correlation
    n = len(ml_scores)
    ml_mean = sum(ml_scores) / n
    rb_mean = sum(rb_scores) / n
    num = sum((ml_scores[i] - ml_mean) * (rb_scores[i] - rb_mean) for i in range(n))
    den_ml = sum((v - ml_mean) ** 2 for v in ml_scores) ** 0.5
    den_rb = sum((v - rb_mean) ** 2 for v in rb_scores) ** 0.5

    if den_ml > 0 and den_rb > 0:
        corr = num / (den_ml * den_rb)
        assert corr > 0.3, f"ML/rule correlation too low: {corr:.2f}"
