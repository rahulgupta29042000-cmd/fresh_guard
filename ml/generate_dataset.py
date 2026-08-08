"""Generate a synthetic historical-orders dataset for Phase 1.

This is NOT real operational data. It is built from hand-picked, realistic
correlations (fragile items -> more damage, high warehouse load -> more
damage, longer distance -> more damage, etc.) plus random noise, so a model
trained on it learns a believable-but-synthetic risk pattern. Run this
before train_model.py.
"""
import os

import numpy as np
import pandas as pd

from feature_schema import FEATURE_COLUMNS, LABEL_COLUMN

RNG = np.random.default_rng(42)
N_ROWS = 7000


def generate_rows(n: int) -> pd.DataFrame:
    n_items = RNG.integers(1, 25, n)
    n_distinct_skus = np.clip((n_items * RNG.uniform(0.4, 0.9, n)).astype(int), 1, n_items)
    total_weight_kg = np.round(n_items * RNG.uniform(0.2, 1.2, n), 2)

    avg_fragility = np.clip(RNG.normal(35, 22, n), 0, 100)
    max_fragility = np.clip(avg_fragility + RNG.uniform(0, 40, n), 0, 100)
    n_fragile_items = np.clip((n_items * (avg_fragility / 140)).astype(int), 0, n_items)

    n_temperature_sensitive_items = np.clip(
        (n_items * RNG.uniform(0, 0.35, n)).astype(int), 0, n_items
    )
    avg_historical_damage_rate = np.clip(RNG.normal(0.08, 0.06, n), 0.005, 0.6)

    distance_km = np.round(np.clip(RNG.normal(6, 4, n), 0.5, 30), 2)

    warehouse_load_ratio = np.clip(RNG.normal(0.7, 0.35, n), 0.05, 2.0)
    hour_of_day = RNG.integers(0, 24, n)
    is_peak_hour = np.isin(hour_of_day, [8, 9, 10, 18, 19, 20, 21]).astype(int)

    picker_experience_years = np.clip(RNG.normal(2.2, 1.6, n), 0.05, 12)
    picker_avg_quality_score = np.clip(RNG.normal(82, 10, n), 40, 100)
    picker_avg_picking_speed = np.clip(RNG.normal(6.5, 1.8, n), 1.5, 14)

    rider_experience_years = np.clip(RNG.normal(2.0, 1.5, n), 0.05, 12)
    rider_avg_rating = np.clip(RNG.normal(4.4, 0.4, n), 2.5, 5.0)

    df = pd.DataFrame(
        {
            "n_items": n_items,
            "n_distinct_skus": n_distinct_skus,
            "total_weight_kg": total_weight_kg,
            "max_fragility": max_fragility,
            "avg_fragility": avg_fragility,
            "n_fragile_items": n_fragile_items,
            "n_temperature_sensitive_items": n_temperature_sensitive_items,
            "avg_historical_damage_rate": avg_historical_damage_rate,
            "distance_km": distance_km,
            "warehouse_load_ratio": warehouse_load_ratio,
            "is_peak_hour": is_peak_hour,
            "picker_experience_years": picker_experience_years,
            "picker_avg_quality_score": picker_avg_quality_score,
            "picker_avg_picking_speed": picker_avg_picking_speed,
            "rider_experience_years": rider_experience_years,
            "rider_avg_rating": rider_avg_rating,
            "hour_of_day": hour_of_day,
        }
    )
    return df


def label_from_features(df: pd.DataFrame) -> np.ndarray:
    """A hand-tuned linear-in-logit model of "true" damage-issue probability.

    Coefficients encode the domain assumptions from the product brief
    (fragility, complexity, warehouse load, handling quality, distance,
    temperature sensitivity all push risk up). Noise keeps it learnable
    but not deterministic, like real-world data would be.
    """
    z = (
        -6.8
        + 0.05 * df["max_fragility"]
        + 0.015 * df["avg_fragility"]
        + 0.30 * df["n_fragile_items"]
        + 0.05 * df["n_items"]
        + 0.04 * df["n_distinct_skus"]
        + 5.0 * df["avg_historical_damage_rate"]
        + 0.30 * df["n_temperature_sensitive_items"]
        + 0.05 * df["distance_km"]
        + 2.0 * df["warehouse_load_ratio"]
        + 1.2 * df["is_peak_hour"]
        - 0.18 * df["picker_experience_years"]
        - 0.014 * df["picker_avg_quality_score"]
        - 0.08 * df["rider_experience_years"]
        - 0.25 * df["rider_avg_rating"]
    )
    noise = RNG.normal(0, 1.1, len(df))
    prob = 1 / (1 + np.exp(-(z + noise)))
    return RNG.binomial(1, prob)


def main():
    df = generate_rows(N_ROWS)
    df[LABEL_COLUMN] = label_from_features(df)
    df = df[FEATURE_COLUMNS + [LABEL_COLUMN]]

    out_path = os.path.join(os.path.dirname(__file__), "dataset.csv")
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path}")
    print(f"Positive rate (had_quality_issue=1): {df[LABEL_COLUMN].mean():.3f}")


if __name__ == "__main__":
    main()
