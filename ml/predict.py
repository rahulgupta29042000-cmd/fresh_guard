"""Standalone prediction helper. The backend's risk_engine.py loads the
same model.pkl the same way — this module is also usable directly from
the CLI for quick manual checks of the trained model.
"""
import json
import os
import sys

import joblib
import pandas as pd

from feature_schema import FEATURE_COLUMNS

HERE = os.path.dirname(__file__)
_bundle = None


def load_model():
    global _bundle
    if _bundle is None:
        model_path = os.path.join(HERE, "model.pkl")
        if not os.path.exists(model_path):
            raise FileNotFoundError("model.pkl not found — run train_model.py first")
        _bundle = joblib.load(model_path)
    return _bundle


def predict_probability(features: dict) -> float:
    bundle = load_model()
    model = bundle["model"]
    row = pd.DataFrame([[features[col] for col in FEATURE_COLUMNS]], columns=FEATURE_COLUMNS)
    return float(model.predict_proba(row)[0][1])


if __name__ == "__main__":
    example = {
        "n_items": 12,
        "n_distinct_skus": 5,
        "total_weight_kg": 4.8,
        "max_fragility": 85,
        "avg_fragility": 40,
        "n_fragile_items": 1,
        "n_temperature_sensitive_items": 1,
        "avg_historical_damage_rate": 0.09,
        "distance_km": 5.2,
        "warehouse_load_ratio": 1.3,
        "is_peak_hour": 1,
        "picker_experience_years": 1.5,
        "picker_avg_quality_score": 78,
        "picker_avg_picking_speed": 5.5,
        "rider_experience_years": 1.2,
        "rider_avg_rating": 4.2,
        "hour_of_day": 19,
    }
    features = json.loads(sys.argv[1]) if len(sys.argv) > 1 else example
    prob = predict_probability(features)
    print(json.dumps({"probability": prob, "riskScore": round(prob * 100)}, indent=2))
