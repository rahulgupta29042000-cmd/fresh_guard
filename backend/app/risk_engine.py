"""Fresh_Guard Phase 1 risk engine.

Builds the feature vector for an order, calls the trained ML model for
the headline risk score, and independently computes an interpretable
component breakdown + human-readable risk factors used for the
explainability panel. If the ML model can't be loaded or fails, the
engine falls back to a rule-based score built from the same components
so the app keeps working (see config.COMPONENT_WEIGHTS).
"""
import os
import sys
from typing import List

from . import config

ML_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ml")
if ML_DIR not in sys.path:
    sys.path.insert(0, ML_DIR)

_model_bundle = None
_model_load_failed = False


def _try_load_model():
    global _model_bundle, _model_load_failed
    if _model_bundle is not None or _model_load_failed:
        return _model_bundle
    try:
        import joblib

        _model_bundle = joblib.load(config.MODEL_PATH)
    except Exception:
        _model_load_failed = True
        _model_bundle = None
    return _model_bundle


def _is_peak_hour(hour: int) -> bool:
    return any(lo <= hour <= hi for lo, hi in config.PEAK_HOURS)


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


DEFAULT_PICKER_STATS = {"experience_years": 1.5, "avg_quality_score": 75.0, "avg_picking_speed": 5.5}
DEFAULT_RIDER_STATS = {"experience_years": 1.5, "avg_rating": 4.0}


def build_features(order, items, warehouse, picker, rider) -> dict:
    fragility_scores = [it["fragility_score"] for it in items for _ in range(it["quantity"])]
    weights = [it["weight_kg"] for it in items for _ in range(it["quantity"])]
    n_items = sum(it["quantity"] for it in items)
    n_distinct_skus = len(items)
    total_weight_kg = round(sum(w for w in weights), 2) if weights else 0.0
    avg_fragility = sum(fragility_scores) / len(fragility_scores) if fragility_scores else 0.0
    max_fragility = max(fragility_scores) if fragility_scores else 0.0
    n_fragile_items = sum(it["quantity"] for it in items if it["fragility_score"] >= 60)
    n_temp_items = sum(it["quantity"] for it in items if it["temperature_sensitive"])
    avg_hist_damage = (
        sum(it["historical_damage_rate"] for it in items) / len(items) if items else 0.0
    )

    warehouse_load_ratio = (warehouse.current_load / warehouse.capacity) if warehouse and warehouse.capacity else 0.5
    hour = order.order_time.hour if order.order_time else 12
    is_peak = 1 if _is_peak_hour(hour) else 0

    picker_stats = (
        {
            "experience_years": picker.experience_years,
            "avg_quality_score": picker.avg_quality_score,
            "avg_picking_speed": picker.avg_picking_speed,
        }
        if picker
        else DEFAULT_PICKER_STATS
    )
    rider_stats = (
        {"experience_years": rider.experience_years, "avg_rating": rider.avg_rating}
        if rider
        else DEFAULT_RIDER_STATS
    )

    return {
        "n_items": n_items,
        "n_distinct_skus": n_distinct_skus,
        "total_weight_kg": total_weight_kg,
        "max_fragility": max_fragility,
        "avg_fragility": avg_fragility,
        "n_fragile_items": n_fragile_items,
        "n_temperature_sensitive_items": n_temp_items,
        "avg_historical_damage_rate": avg_hist_damage,
        "distance_km": order.distance_km,
        "warehouse_load_ratio": warehouse_load_ratio,
        "is_peak_hour": is_peak,
        "picker_experience_years": picker_stats["experience_years"],
        "picker_avg_quality_score": picker_stats["avg_quality_score"],
        "picker_avg_picking_speed": picker_stats["avg_picking_speed"],
        "rider_experience_years": rider_stats["experience_years"],
        "rider_avg_rating": rider_stats["avg_rating"],
        "hour_of_day": hour,
    }


def compute_component_scores(features: dict) -> dict:
    product_risk = _clamp(
        0.40 * features["avg_fragility"]
        + 0.30 * features["max_fragility"]
        + 20.0 * features["avg_historical_damage_rate"]
        + (15 if features["n_temperature_sensitive_items"] > 0 else 0)
    )
    order_complexity = _clamp(
        features["n_items"] * 4.0 + features["n_distinct_skus"] * 3.0 + features["total_weight_kg"] * 2.0
    )
    warehouse_risk = _clamp(features["warehouse_load_ratio"] * 60.0 + (20 if features["is_peak_hour"] else 0))
    delivery_risk = _clamp(
        20
        + features["distance_km"] * 7.0
        - features["rider_experience_years"] * 2.0
        - (features["rider_avg_rating"] - 4.0) * 15.0
    )
    handling_risk = _clamp(
        90
        - features["picker_avg_quality_score"] * 0.6
        - features["picker_experience_years"] * 2.5
        + features["n_fragile_items"] * 10.0
        + features["n_temperature_sensitive_items"] * 6.0
    )
    temperature_risk = _clamp(features["n_temperature_sensitive_items"] * 35.0)

    return {
        "product_risk": round(product_risk, 1),
        "order_complexity": round(order_complexity, 1),
        "warehouse_risk": round(warehouse_risk, 1),
        "delivery_risk": round(delivery_risk, 1),
        "handling_risk": round(handling_risk, 1),
        "temperature_risk": round(temperature_risk, 1),
    }


def rule_based_score(components: dict) -> float:
    return sum(components[key] * weight for key, weight in config.COMPONENT_WEIGHTS.items())


def _impact_rank(impact: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(impact, 3)


def build_risk_factors(features: dict, items: List[dict]) -> List[dict]:
    factors = []

    fragile_items = sorted((it for it in items if it["fragility_score"] >= 60), key=lambda i: -i["fragility_score"])
    if fragile_items:
        factors.append({"factor": f"Fragile item: {fragile_items[0]['name']}", "impact": "high"})
    elif features["max_fragility"] >= 40:
        factors.append({"factor": "Contains a moderately fragile item", "impact": "medium"})

    if features["n_items"] >= 15:
        factors.append({"factor": f"Large order with {features['n_items']} items", "impact": "high"})
    elif features["n_items"] >= 8:
        factors.append({"factor": f"Large order with {features['n_items']} items", "impact": "medium"})

    if features["warehouse_load_ratio"] >= 1.3:
        factors.append({"factor": "High warehouse workload", "impact": "high"})
    elif features["warehouse_load_ratio"] >= 0.9:
        factors.append({"factor": "Elevated warehouse workload", "impact": "medium"})

    if features["distance_km"] >= 12:
        factors.append({"factor": f"Long delivery distance ({features['distance_km']} km)", "impact": "high"})
    elif features["distance_km"] >= 4:
        factors.append({"factor": f"{features['distance_km']} km delivery distance", "impact": "medium"})

    if features["n_temperature_sensitive_items"] >= 1:
        temp_items = [it["name"] for it in items if it["temperature_sensitive"]]
        factors.append(
            {
                "factor": f"Temperature-sensitive product: {', '.join(temp_items[:2])}",
                "impact": "medium" if features["n_temperature_sensitive_items"] == 1 else "high",
            }
        )

    if features["picker_avg_quality_score"] < 70:
        factors.append({"factor": "Order may benefit from extra picking guidance", "impact": "medium"})

    if features["is_peak_hour"]:
        factors.append({"factor": "Placed during a peak operational period", "impact": "low"})

    factors.sort(key=lambda f: _impact_rank(f["impact"]))
    return factors[:5]


def assess_risk(order, items: List[dict], warehouse, picker, rider) -> dict:
    """items: list of {name, category, fragility_score, temperature_sensitive,
    weight_kg, historical_damage_rate, quantity}."""
    features = build_features(order, items, warehouse, picker, rider)
    components = compute_component_scores(features)

    bundle = _try_load_model()
    if bundle is not None:
        try:
            import pandas as pd

            row = pd.DataFrame([[features[c] for c in bundle["feature_columns"]]], columns=bundle["feature_columns"])
            probability = float(bundle["model"].predict_proba(row)[0][1])
            score = round(_clamp(probability * 100))
            source = "ml_model"
            model_version = bundle.get("model_version", config.MODEL_VERSION)
        except Exception:
            score = round(rule_based_score(components))
            source = "rule_based_fallback"
            model_version = config.MODEL_VERSION
    else:
        score = round(rule_based_score(components))
        source = "rule_based_fallback"
        model_version = config.MODEL_VERSION

    level = config.risk_level_for_score(score)
    factors = build_risk_factors(features, items)

    return {
        "risk_score": score,
        "risk_level": level,
        "model_version": model_version,
        "prediction_source": source,
        "component_scores": {
            "product_risk": components["product_risk"],
            "order_complexity": components["order_complexity"],
            "warehouse_risk": components["warehouse_risk"],
            "delivery_risk": components["delivery_risk"],
            "handling_risk": components["handling_risk"],
        },
        "risk_factors": factors,
    }
