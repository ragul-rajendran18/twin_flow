"""Model loading and inference helpers shared by the API and scripts.

The :class:`ModelRegistry` loads the four Joblib artifacts once and keeps the
feature ordering identical to training.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from app.config import settings
from ml.generate_dataset import FEATURE_COLUMNS

MODEL_FILES = {
    "congestion": "congestion_model.joblib",
    "bottleneck": "bottleneck_model.joblib",
    "queue": "queue_model.joblib",
    "delay": "delay_model.joblib",
}


class ModelNotTrainedError(RuntimeError):
    """Raised when model artifacts are missing or incomplete."""


@dataclass
class ModelPrediction:
    congestion_probability: float
    congestion_class: int
    congestion_level: str
    bottleneck_probability: float
    bottleneck_detected: bool
    predicted_queue_length: float
    predicted_delay_minutes: float
    model_version: str


class ModelRegistry:
    """Loads and caches model artifacts for inference."""

    def __init__(self, artifacts_dir: Path | None = None) -> None:
        self.artifacts_dir = Path(artifacts_dir) if artifacts_dir else settings.artifacts_path
        self._loaded = False
        self._models: dict[str, Any] = {}
        self._metadata: dict[str, Any] = {}
        self.feature_columns: list[str] = list(FEATURE_COLUMNS)

    @property
    def model_version(self) -> str:
        return self._metadata.get("model_version", "unknown")

    def is_available(self) -> bool:
        required = list(MODEL_FILES.values()) + ["metadata.json"]
        return all((self.artifacts_dir / name).exists() for name in required)

    def load(self, force: bool = False) -> None:
        if self._loaded and not force:
            return
        missing = [name for name in list(MODEL_FILES.values()) + ["metadata.json"] if not (self.artifacts_dir / name).exists()]
        if missing:
            raise ModelNotTrainedError(
                "Model artifacts are missing: "
                + ", ".join(missing)
                + f" (looked in {self.artifacts_dir}). "
                + "Generate the dataset with 'python -m ml.generate_dataset' and train with "
                + "'python -m ml.train_model'."
            )
        self._models = {key: joblib.load(self.artifacts_dir / filename) for key, filename in MODEL_FILES.items()}
        self._metadata = json.loads((self.artifacts_dir / "metadata.json").read_text(encoding="utf-8"))
        self.feature_columns = self._metadata.get("feature_columns", list(FEATURE_COLUMNS))
        self._loaded = True

    def _feature_vector(self, features: dict[str, float]) -> np.ndarray:
        missing = [c for c in self.feature_columns if c not in features]
        if missing:
            raise ValueError(f"Missing required features: {missing}")
        return np.array([[float(features[c]) for c in self.feature_columns]], dtype=float)

    def predict(self, features: dict[str, float]) -> ModelPrediction:
        self.load()
        X = self._feature_vector(features)
        congestion_proba = self._models["congestion"].predict_proba(X)[0]
        congestion_class = int(self._models["congestion"].predict(X)[0])
        # Probability of the predicted class (documented as the congestion score).
        congestion_probability = float(congestion_proba[congestion_class])
        # Guard against unseen class ordering.
        classes = list(self._models["congestion"].classes_)
        if congestion_class not in classes:
            congestion_class = int(classes[int(np.argmax(congestion_proba))])
            congestion_probability = float(congestion_proba[int(np.argmax(congestion_proba))])

        level = self.level_from_probability(congestion_probability)

        bottleneck_proba = self._models["bottleneck"].predict_proba(X)[0]
        classes_b = list(self._models["bottleneck"].classes_)
        if 1 in classes_b:
            bottleneck_probability = float(bottleneck_proba[classes_b.index(1)])
        else:
            bottleneck_probability = 0.0

        queue_value = float(np.clip(self._models["queue"].predict(X)[0], 0, None))
        delay_value = float(np.clip(self._models["delay"].predict(X)[0], 0, None))

        return ModelPrediction(
            congestion_probability=round(congestion_probability, 4),
            congestion_class=congestion_class,
            congestion_level=level,
            bottleneck_probability=round(bottleneck_probability, 4),
            bottleneck_detected=bottleneck_probability >= settings.bottleneck_threshold,
            predicted_queue_length=round(queue_value, 2),
            predicted_delay_minutes=round(delay_value, 2),
            model_version=self.model_version,
        )

    @staticmethod
    def level_from_probability(probability: float) -> str:
        """Map a congestion probability to a documented level.

        LOW: probability < moderate threshold.
        MODERATE: moderate threshold <= probability < high threshold.
        HIGH: probability >= high threshold.
        """
        if probability >= settings.congestion_threshold_high:
            return "HIGH"
        if probability >= settings.congestion_threshold_moderate:
            return "MODERATE"
        return "LOW"


_registry: ModelRegistry | None = None


def get_model_registry() -> ModelRegistry:
    """Return a process-wide cached model registry."""
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry
