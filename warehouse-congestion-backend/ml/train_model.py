"""Train the warehouse congestion and bottleneck models.

Trains four Scikit-learn estimators and persists them with Joblib:

* ``congestion_model.joblib`` - RandomForestClassifier (LOW / MODERATE / HIGH)
* ``bottleneck_model.joblib`` - RandomForestClassifier (0 / 1)
* ``queue_model.joblib`` - RandomForestRegressor (future queue length)
* ``delay_model.joblib`` - RandomForestRegressor (future delay minutes)

Usage:
    python -m ml.train_model --dataset ml/artifacts/dataset.csv
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    mean_absolute_error,
    mean_squared_error,
)
from sklearn.model_selection import train_test_split

from ml.generate_dataset import FEATURE_COLUMNS, LABEL_COLUMNS

MODEL_VERSION = "1.0.0"


def _load_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = FEATURE_COLUMNS + LABEL_COLUMNS
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset missing required columns: {missing}")
    return df


def train(dataset_path: Path, artifacts_dir: Path) -> dict:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    df = _load_dataset(dataset_path)

    X = df[FEATURE_COLUMNS].values
    y_congestion = df["congestion_label"].values
    y_bottleneck = df["bottleneck_label"].values
    y_queue = df["future_queue_length"].values
    y_delay = df["future_delay_minutes"].values

    # Single split shared by all models so there is no leakage between the
    # training set and the final evaluation set.
    X_train, X_test, ycon_train, ycon_test, ybot_train, ybot_test, yq_train, yq_test, yd_train, yd_test = (
        train_test_split(
            X,
            y_congestion,
            y_bottleneck,
            y_queue,
            y_delay,
            test_size=0.2,
            random_state=42,
            stratify=y_congestion,
        )
    )

    rf_common = dict(n_estimators=100, random_state=42, n_jobs=-1)

    congestion_model = RandomForestClassifier(**rf_common)
    congestion_model.fit(X_train, ycon_train)

    bottleneck_model = RandomForestClassifier(**rf_common)
    bottleneck_model.fit(X_train, ybot_train)

    queue_model = RandomForestRegressor(**rf_common)
    queue_model.fit(X_train, yq_train)

    delay_model = RandomForestRegressor(**rf_common)
    delay_model.fit(X_train, yd_train)

    # --- Evaluation ---
    ycon_pred = congestion_model.predict(X_test)
    ybot_pred = bottleneck_model.predict(X_test)
    yq_pred = np.clip(queue_model.predict(X_test), 0, None)
    yd_pred = np.clip(delay_model.predict(X_test), 0, None)

    report = {
        "congestion": classification_report(ycon_test, ycon_pred, zero_division=0, output_dict=True),
        "congestion_confusion_matrix": confusion_matrix(ycon_test, ycon_pred).tolist(),
        "bottleneck": classification_report(ybot_test, ybot_pred, zero_division=0, output_dict=True),
        "bottleneck_confusion_matrix": confusion_matrix(ybot_test, ybot_pred).tolist(),
        "queue_mae": float(mean_absolute_error(yq_test, yq_pred)),
        "queue_rmse": float(np.sqrt(mean_squared_error(yq_test, yq_pred))),
        "delay_mae": float(mean_absolute_error(yd_test, yd_pred)),
        "delay_rmse": float(np.sqrt(mean_squared_error(yd_test, yd_pred))),
    }

    # --- Persist artifacts ---
    joblib.dump(congestion_model, artifacts_dir / "congestion_model.joblib")
    joblib.dump(bottleneck_model, artifacts_dir / "bottleneck_model.joblib")
    joblib.dump(queue_model, artifacts_dir / "queue_model.joblib")
    joblib.dump(delay_model, artifacts_dir / "delay_model.joblib")

    metadata = {
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_training_rows": int(len(X_train)),
        "n_test_rows": int(len(X_test)),
        "feature_columns": FEATURE_COLUMNS,
        "label_columns": LABEL_COLUMNS,
        "congestion_classes": [int(c) for c in sorted(np.unique(y_congestion))],
        "bottleneck_classes": [int(c) for c in sorted(np.unique(y_bottleneck))],
        "evaluation": report,
    }
    (artifacts_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    # --- Console training report ---
    print("=" * 72)
    print(f"MODEL VERSION: {MODEL_VERSION}")
    print(f"Training rows: {len(X_train)}  Test rows: {len(X_test)}")
    print("=" * 72)
    print("\n[Congestion classifier] classes: 0=LOW 1=MODERATE 2=HIGH")
    print(classification_report(ycon_test, ycon_pred, zero_division=0))
    print("Confusion matrix:")
    print(confusion_matrix(ycon_test, ycon_pred))
    print("\n[Bottleneck classifier] classes: 0=none 1=bottleneck")
    print(classification_report(ybot_test, ybot_pred, zero_division=0))
    print("Confusion matrix:")
    print(confusion_matrix(ybot_test, ybot_pred))
    print("\n[Queue regressor]  MAE=%.3f  RMSE=%.3f" % (report["queue_mae"], report["queue_rmse"]))
    print("[Delay regressor]  MAE=%.3f  RMSE=%.3f" % (report["delay_mae"], report["delay_rmse"]))
    print("=" * 72)
    print(f"Artifacts saved to {artifacts_dir}")
    return metadata


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Train warehouse congestion models")
    parser.add_argument("--dataset", type=str, default="ml/artifacts/dataset.csv")
    parser.add_argument("--artifacts", type=str, default="ml/artifacts")
    args = parser.parse_args(argv)
    train(Path(args.dataset), Path(args.artifacts))


if __name__ == "__main__":
    main()
