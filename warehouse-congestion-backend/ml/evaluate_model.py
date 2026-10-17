"""Evaluate persisted model artifacts against the synthetic dataset.

Usage:
    python -m ml.evaluate_model --dataset ml/artifacts/dataset.csv
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    recall_score,
)

from ml.generate_dataset import FEATURE_COLUMNS


def evaluate(dataset_path: Path, artifacts_dir: Path) -> dict:
    df = pd.read_csv(dataset_path)
    metadata_path = artifacts_dir / "metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(
            "metadata.json not found. Train the models first: python -m ml.train_model"
        )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    congestion_model = joblib.load(artifacts_dir / "congestion_model.joblib")
    bottleneck_model = joblib.load(artifacts_dir / "bottleneck_model.joblib")
    queue_model = joblib.load(artifacts_dir / "queue_model.joblib")
    delay_model = joblib.load(artifacts_dir / "delay_model.joblib")

    X = df[FEATURE_COLUMNS].values
    results: dict = {}

    ycon = df["congestion_label"].values
    ycon_pred = congestion_model.predict(X)
    results["congestion"] = {
        "accuracy": float(accuracy_score(ycon, ycon_pred)),
        "precision_macro": float(precision_score(ycon, ycon_pred, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(ycon, ycon_pred, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(ycon, ycon_pred, average="macro", zero_division=0)),
        "confusion_matrix": confusion_matrix(ycon, ycon_pred).tolist(),
    }

    ybot = df["bottleneck_label"].values
    ybot_pred = bottleneck_model.predict(X)
    results["bottleneck"] = {
        "accuracy": float(accuracy_score(ybot, ybot_pred)),
        "precision": float(precision_score(ybot, ybot_pred, zero_division=0)),
        "recall": float(recall_score(ybot, ybot_pred, zero_division=0)),
        "f1": float(f1_score(ybot, ybot_pred, zero_division=0)),
        "confusion_matrix": confusion_matrix(ybot, ybot_pred).tolist(),
    }

    yq = df["future_queue_length"].values
    yq_pred = np.clip(queue_model.predict(X), 0, None)
    results["queue"] = {
        "mae": float(mean_absolute_error(yq, yq_pred)),
        "rmse": float(np.sqrt(mean_squared_error(yq, yq_pred))),
    }

    yd = df["future_delay_minutes"].values
    yd_pred = np.clip(delay_model.predict(X), 0, None)
    results["delay"] = {
        "mae": float(mean_absolute_error(yd, yd_pred)),
        "rmse": float(np.sqrt(mean_squared_error(yd, yd_pred))),
    }

    print("=" * 72)
    print(f"MODEL VERSION: {metadata.get('model_version')} (trained {metadata.get('trained_at')})")
    print(f"Evaluating on synthetic dataset with {len(df)} rows")
    print("NOTE: metrics reflect recovery of synthetic labelling rules only.")
    print("=" * 72)
    print(json.dumps(results, indent=2))
    return results


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Evaluate warehouse congestion models")
    parser.add_argument("--dataset", type=str, default="ml/artifacts/dataset.csv")
    parser.add_argument("--artifacts", type=str, default="ml/artifacts")
    args = parser.parse_args(argv)
    evaluate(Path(args.dataset), Path(args.artifacts))


if __name__ == "__main__":
    main()
