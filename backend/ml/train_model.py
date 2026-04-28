"""
XGBoost risk scoring model trainer with SHAP explainability.

Pipeline:
  1. Load (or generate) dataset.csv
  2. Train/test split (80/20, stratified)
  3. Train XGBoostClassifier
  4. Evaluate: accuracy, AUC, classification report
  5. Save model.joblib  →  loaded lazily by risk_scorer.MLScorer

Usage:
    python ml/train_model.py               # generates fresh data then trains
    python ml/train_model.py --no-regen    # reuse existing dataset.csv
    python ml/train_model.py --rows 5000   # generate larger dataset
"""

from __future__ import annotations
import argparse
import os
import sys
import json

# Allow running from project root or backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

ML_DIR = os.path.dirname(__file__)
DATASET_PATH = os.path.join(ML_DIR, "dataset.csv")
MODEL_PATH = os.path.join(ML_DIR, "model.joblib")
METRICS_PATH = os.path.join(ML_DIR, "metrics.json")


def load_dataset(path: str):
    import pandas as pd
    df = pd.read_csv(path)
    print(f"[train] Loaded dataset: {len(df)} rows, {len(df.columns)} columns")
    print(f"[train] Label distribution:\n{df['label'].value_counts().to_string()}")
    return df


def train(df, n_estimators: int = 200, max_depth: int = 5):
    import numpy as np
    import pandas as pd
    from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
    from sklearn.metrics import (
        accuracy_score, roc_auc_score, classification_report,
        average_precision_score
    )
    import xgboost as xgb
    import joblib

    from ml.feature_config import FEATURE_NAMES

    X = df[FEATURE_NAMES].values
    y = df["label"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    # Class balance
    neg, pos = int((y_train == 0).sum()), int((y_train == 1).sum())
    scale_pos_weight = neg / pos if pos > 0 else 1.0

    model = xgb.XGBClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        eval_metric="auc",
        random_state=42,
        n_jobs=-1,
    )

    print(f"[train] Training XGBoost (n_estimators={n_estimators}, max_depth={max_depth}) ...")
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    # ── Evaluation ───────────────────────────────────────────────────────────
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_proba)
    ap = average_precision_score(y_test, y_proba)

    print(f"\n[train] === Evaluation on held-out test set ===")
    print(f"  Accuracy  : {acc:.4f}")
    print(f"  ROC-AUC   : {auc:.4f}")
    print(f"  Avg Prec  : {ap:.4f}")
    print(f"\n{classification_report(y_test, y_pred, target_names=['Low/Med', 'High/Critical'])}")

    # 5-fold CV AUC
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_aucs = cross_val_score(model, X, y, cv=cv, scoring="roc_auc")
    print(f"[train] 5-fold CV AUC: {cv_aucs.mean():.4f} ± {cv_aucs.std():.4f}")

    # ── Feature importance ────────────────────────────────────────────────────
    importances = dict(zip(FEATURE_NAMES, model.feature_importances_.tolist()))
    sorted_imp = sorted(importances.items(), key=lambda x: x[1], reverse=True)
    print("\n[train] Feature importance (gain):")
    for feat, imp in sorted_imp:
        print(f"  {feat:<30s} {imp:.4f}")

    # ── Save model ────────────────────────────────────────────────────────────
    joblib.dump(model, MODEL_PATH)
    print(f"\n[train] Model saved → {MODEL_PATH}")

    # ── Save metrics ─────────────────────────────────────────────────────────
    metrics = {
        "accuracy": round(acc, 4),
        "roc_auc": round(auc, 4),
        "avg_precision": round(ap, 4),
        "cv_auc_mean": round(float(cv_aucs.mean()), 4),
        "cv_auc_std": round(float(cv_aucs.std()), 4),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "feature_importance": {k: round(v, 4) for k, v in sorted_imp},
    }
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"[train] Metrics saved → {METRICS_PATH}")

    # ── SHAP sanity check ─────────────────────────────────────────────────────
    try:
        import shap
        explainer = shap.TreeExplainer(model)
        shap_vals = explainer.shap_values(X_test[:50])
        mean_abs_shap = dict(zip(FEATURE_NAMES, abs(shap_vals).mean(axis=0).tolist()))
        sorted_shap = sorted(mean_abs_shap.items(), key=lambda x: x[1], reverse=True)
        print("\n[train] SHAP mean |value| on test slice:")
        for feat, val in sorted_shap:
            print(f"  {feat:<30s} {val:.4f}")
        metrics["shap_importance"] = {k: round(v, 4) for k, v in sorted_shap}
        with open(METRICS_PATH, "w") as f:
            json.dump(metrics, f, indent=2)
        print("[train] SHAP OK — metrics updated")
    except Exception as e:
        print(f"[train] SHAP skipped: {e}")

    return model, metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train XGBoost risk scoring model")
    parser.add_argument("--no-regen", action="store_true", help="Reuse existing dataset.csv")
    parser.add_argument("--rows", type=int, default=3000, help="Dataset rows to generate")
    parser.add_argument("--estimators", type=int, default=200, help="XGBoost n_estimators")
    parser.add_argument("--depth", type=int, default=5, help="XGBoost max_depth")
    args = parser.parse_args()

    # Generate dataset if needed
    if not args.no_regen or not os.path.exists(DATASET_PATH):
        print(f"[train] Generating dataset ({args.rows} rows) ...")
        from ml.generate_dataset import generate, write_csv
        rows = generate(args.rows)
        write_csv(rows, DATASET_PATH)
    else:
        print(f"[train] Reusing existing dataset: {DATASET_PATH}")

    df = load_dataset(DATASET_PATH)
    train(df, n_estimators=args.estimators, max_depth=args.depth)
    print("\n[train] Done. Run the backend — MLScorer will auto-load model.joblib")
