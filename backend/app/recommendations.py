"""Risk-based recommendation engine.

Deliberately separate from the ML model: it turns a risk LEVEL plus
order/item context into concrete operational instructions. If the model
is unavailable, risk_engine falls back to a rule-based score, and this
engine still runs unchanged — so recommendations never depend on the ML
model being up.
"""
from typing import Dict, List

PRODUCE_CATEGORIES = {"produce"}
LIGHTWEIGHT_CATEGORIES = {"snacks", "packaged"}

BASELINE_BY_LEVEL: Dict[str, List[dict]] = {
    "LOW": [
        {
            "type": "info",
            "instruction": "Normal fulfillment — no additional intervention required.",
            "priority": "low",
        }
    ],
    "MEDIUM": [
        {
            "type": "picker_reminder",
            "instruction": "Show picker quality-handling reminders before packing.",
            "priority": "medium",
        }
    ],
    "HIGH": [
        {"type": "inspection", "instruction": "Manual quality inspection before packing.", "priority": "high"},
        {"type": "packing", "instruction": "Apply special packing recommendation for this order.", "priority": "high"},
        {"type": "delivery", "instruction": "Send delivery handling alert to the assigned rider.", "priority": "high"},
    ],
    "CRITICAL": [
        {"type": "inspection", "instruction": "Manual QC review required before dispatch.", "priority": "critical"},
        {"type": "packing", "instruction": "Use reinforced/insulated packaging as applicable.", "priority": "critical"},
        {"type": "delivery", "instruction": "Priority dispatch — minimize transit time.", "priority": "critical"},
        {"type": "manager_alert", "instruction": "Flag order for manager visibility.", "priority": "critical"},
    ],
}


def generate_recommendations(risk_level: str, items: List[dict], distance_km: float) -> List[dict]:
    """items: list of {name, category, fragility_score, temperature_sensitive, weight_kg}."""
    recs = list(BASELINE_BY_LEVEL.get(risk_level, BASELINE_BY_LEVEL["LOW"]))

    for item in items:
        name = item["name"]
        category = item["category"]
        fragility = item["fragility_score"]
        temp_sensitive = item["temperature_sensitive"]
        weight = item["weight_kg"]

        if fragility >= 65:
            recs.append(
                {
                    "type": "handling",
                    "instruction": f"Handle {name} separately — fragile item.",
                    "priority": "high",
                }
            )
        elif category in PRODUCE_CATEGORIES and fragility >= 35:
            recs.append(
                {
                    "type": "inspection",
                    "instruction": f"Inspect {name} before packing.",
                    "priority": "medium",
                }
            )

        if temp_sensitive:
            recs.append(
                {
                    "type": "handling",
                    "instruction": f"Keep {name} temperature-protected.",
                    "priority": "high" if risk_level in ("HIGH", "CRITICAL") else "medium",
                }
            )

        if category in LIGHTWEIGHT_CATEGORIES and weight < 0.4:
            recs.append(
                {
                    "type": "packing",
                    "instruction": f"Keep {name} above heavier products in the bag.",
                    "priority": "low",
                }
            )

    if distance_km >= 8 and risk_level in ("MEDIUM", "HIGH", "CRITICAL"):
        recs.append(
            {
                "type": "delivery",
                "instruction": f"Long delivery distance ({distance_km} km) — confirm secure loading before dispatch.",
                "priority": "medium",
            }
        )

    # Deduplicate while preserving order.
    seen = set()
    unique_recs = []
    for r in recs:
        key = (r["type"], r["instruction"])
        if key not in seen:
            seen.add(key)
            unique_recs.append(r)
    return unique_recs
