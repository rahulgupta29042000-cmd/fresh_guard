"""Canonical feature list shared by dataset generation, training, and the
live prediction path in backend/app/risk_engine.py. Keeping this in one
place guarantees the model always sees the same feature vector shape it
was trained on.
"""

FEATURE_COLUMNS = [
    "n_items",
    "n_distinct_skus",
    "total_weight_kg",
    "max_fragility",
    "avg_fragility",
    "n_fragile_items",
    "n_temperature_sensitive_items",
    "avg_historical_damage_rate",
    "distance_km",
    "warehouse_load_ratio",
    "is_peak_hour",
    "picker_experience_years",
    "picker_avg_quality_score",
    "picker_avg_picking_speed",
    "rider_experience_years",
    "rider_avg_rating",
    "hour_of_day",
]

LABEL_COLUMN = "had_quality_issue"
