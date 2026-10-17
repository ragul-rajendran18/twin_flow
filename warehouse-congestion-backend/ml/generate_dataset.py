"""Synthetic warehouse dataset generator.

This module produces a *synthetic* labelled dataset used to train the
congestion/bottleneck models. The values are generated from documented
operational rules with controlled random variation — they are **not** real
warehouse measurements.

Because the data is synthetic, model performance reported by
``ml/evaluate_model.py`` reflects how well the models recover the labelling
rules, **not** real-world warehouse accuracy.

Usage:
    python -m ml.generate_dataset --rows 8000 --seed 42
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "occupancy",
    "agv_count",
    "queue_length",
    "order_volume",
    "conveyor_load",
]

LABEL_COLUMNS = [
    "congestion_label",  # 0 = LOW, 1 = MODERATE, 2 = HIGH
    "bottleneck_label",  # 0 = no bottleneck, 1 = bottleneck
    "future_queue_length",
    "future_delay_minutes",
]

RANDOM_SEED = 42


def _congestion_score(occupancy: float, agv_count: int, queue_length: int, conveyor_load: float, order_volume: int) -> float:
    """A continuous congestion score in roughly [0, 1].

    Derived from documented warehouse rules: congestion rises with occupancy,
    AGV density, queueing and conveyor utilisation.
    """
    score = (
        0.40 * (occupancy / 100.0)
        + 0.20 * min(agv_count, 15) / 15.0
        + 0.25 * min(queue_length, 30) / 30.0
        + 0.10 * (conveyor_load / 100.0)
        + 0.05 * min(order_volume, 50) / 50.0
    )
    return float(np.clip(score, 0.0, 1.0))


def generate_dataframe(rows: int = 8000, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Generate a reproducible synthetic dataset."""
    rng = np.random.default_rng(seed)

    occupancy = rng.uniform(0, 100, rows)
    agv_count = rng.integers(0, 15, rows)
    queue_length = rng.integers(0, 30, rows)
    order_volume = rng.integers(0, 50, rows)
    conveyor_load = rng.uniform(0, 100, rows)

    df = pd.DataFrame(
        {
            "occupancy": occupancy,
            "agv_count": agv_count.astype(float),
            "queue_length": queue_length.astype(float),
            "order_volume": order_volume.astype(float),
            "conveyor_load": conveyor_load,
        }
    )

    scores = np.array(
        [
            _congestion_score(o, a, q, c, v)
            for o, a, q, c, v in zip(
                df["occupancy"], df["agv_count"], df["queue_length"], df["conveyor_load"], df["order_volume"]
            )
        ]
    )

    # Congestion label thresholds aligned with the configured inference policy.
    # LOW < 0.40 <= MODERATE < 0.70 <= HIGH, with a small random perturbation
    # so the decision boundaries are not perfectly sharp.
    noisy = scores + rng.normal(0, 0.03, rows)
    congestion_label = np.where(noisy < 0.40, 0, np.where(noisy < 0.70, 1, 2))
    df["congestion_label"] = congestion_label

    # Bottleneck: high occupancy AND high queue strongly indicate a bottleneck.
    bottleneck_prob = np.clip(
        0.5 * (occupancy / 100.0) + 0.5 * (queue_length / 30.0) - 0.25, 0.0, 1.0
    )
    bottleneck_label = (rng.random(rows) < bottleneck_prob).astype(int)
    df["bottleneck_label"] = bottleneck_label

    # Future queue length and delay: monotone increasing functions of the score
    # plus controlled noise, floored at zero.
    future_queue = queue_length * (1.0 + scores) + rng.normal(0, 1.5, rows)
    future_queue = np.clip(future_queue, 0, None)
    future_delay = scores * 20.0 + queue_length * 0.6 + rng.normal(0, 1.0, rows)
    future_delay = np.clip(future_delay, 0, None)
    df["future_queue_length"] = future_queue
    df["future_delay_minutes"] = future_delay

    # Round to sensible precision for cleanliness.
    df["occupancy"] = df["occupancy"].round(2)
    df["conveyor_load"] = df["conveyor_load"].round(2)
    df["agv_count"] = df["agv_count"].astype(int)
    df["queue_length"] = df["queue_length"].astype(int)
    df["order_volume"] = df["order_volume"].astype(int)
    df["future_queue_length"] = df["future_queue_length"].round(2)
    df["future_delay_minutes"] = df["future_delay_minutes"].round(2)
    return df


def save_dataset(df: pd.DataFrame, path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic warehouse dataset")
    parser.add_argument("--rows", type=int, default=8000)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    parser.add_argument("--out", type=str, default="ml/artifacts/dataset.csv")
    args = parser.parse_args(argv)
    df = generate_dataframe(args.rows, args.seed)
    out = save_dataset(df, args.out)
    print(f"Wrote {len(df)} synthetic rows to {out}")


if __name__ == "__main__":
    main()
