"""Central, tweakable configuration for the risk engine.

Thresholds and weights live here so nothing is hard-coded deeper in the
app — tuning Phase 1 behavior should mean editing this file only.
"""
import os

MODEL_VERSION = "v0.1-prototype"

# Damage Risk Score (0-100) -> Risk Level bands.
RISK_THRESHOLDS = {
    "LOW": (0, 30),
    "MEDIUM": (31, 60),
    "HIGH": (61, 80),
    "CRITICAL": (81, 100),
}

# Weights used when the rule-based engine combines component scores into a
# single 0-100 score (used for the explainability breakdown, and as the
# fallback score if the ML model is unavailable).
COMPONENT_WEIGHTS = {
    "product_risk": 0.30,
    "order_complexity": 0.15,
    "warehouse_risk": 0.15,
    "handling_risk": 0.20,
    "delivery_risk": 0.15,
    "temperature_risk": 0.05,
}

PEAK_HOURS = [(8, 10), (18, 21)]  # inclusive local hour ranges treated as peak

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "sqlite:///" + os.path.join(os.path.dirname(os.path.dirname(__file__)), "freshguard.db")
)

MODEL_PATH = os.environ.get(
    "MODEL_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ml", "model.pkl"),
)


def risk_level_for_score(score: float) -> str:
    score = max(0, min(100, round(score)))
    for level, (low, high) in RISK_THRESHOLDS.items():
        if low <= score <= high:
            return level
    return "CRITICAL"
