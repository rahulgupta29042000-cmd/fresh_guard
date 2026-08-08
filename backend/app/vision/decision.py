"""Decision engine — separate from the vision model. Turns a quality
score + defect list into PASS / REVIEW / REJECT. Thresholds are
configurable in app/config.py, not hard-coded here.

Human-in-the-loop rule: a product is never REJECTed solely because the
model is uncertain about a defect — low confidence routes to REVIEW,
never REJECT. REJECT requires either a low overall score or a
high-severity / high-confidence defect.
"""
from .. import config

LOW_CONFIDENCE_THRESHOLD = 0.6
HIGH_CONFIDENCE_THRESHOLD = 0.8


def decide(quality_score: float, defects: list) -> str:
    thresholds = config.VISION_DECISION_THRESHOLDS

    has_high_severity = any(d["severity"] == "high" for d in defects)
    has_high_confidence_medium_plus = any(
        d["severity"] in ("medium", "high") and d["confidence"] >= HIGH_CONFIDENCE_THRESHOLD for d in defects
    )
    has_low_confidence_defect = any(d["confidence"] < LOW_CONFIDENCE_THRESHOLD for d in defects)
    has_medium_severity = any(d["severity"] == "medium" for d in defects)

    if quality_score < thresholds["review_min_score"] or has_high_severity or has_high_confidence_medium_plus:
        return "REJECT"

    if quality_score < thresholds["pass_min_score"] or has_medium_severity or has_low_confidence_defect:
        return "REVIEW"

    return "PASS"


def recommendation_text(status: str, defects: list) -> str:
    if status == "PASS":
        return "No significant visible defects detected. Safe to continue."
    if not defects:
        return "Human review recommended." if status == "REVIEW" else "Visible defect detected — do not pack as-is."
    top = max(defects, key=lambda d: d["confidence"])
    label = top.get("label", top["type"].replace("_", " ").title())
    if status == "REVIEW":
        return f"Possible {label.lower()} detected — inspect the affected area before accepting this product."
    return f"{label} detected — recommend rejecting and selecting a replacement."
