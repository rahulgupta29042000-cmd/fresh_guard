"""Central, tweakable configuration for the risk engine.

Thresholds and weights live here so nothing is hard-coded deeper in the
app — tuning Phase 1 behavior should mean editing this file only.
"""
import os

from dotenv import load_dotenv

# Loads backend/.env if present (see .env.example). Every variable below
# has a working default, so this is optional for local/demo use.
load_dotenv()

MODEL_VERSION = os.environ.get("MODEL_VERSION", "v0.1-prototype")

# Demo mode is on by default for this MVP — seeded data, simulation vision,
# and the reliable FG-10241 walkthrough are all designed around it. Set
# DEMO_MODE=false only once real data sources replace the seed script.
DEMO_MODE = os.environ.get("DEMO_MODE", "true").lower() in ("1", "true", "yes")

# Not read by the simulation provider — present so a future real vision
# provider has a standard place to pick up credentials from, per the
# "never hard-code API keys" requirement.
VISION_API_KEY = os.environ.get("VISION_API_KEY", "")

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


# ---------------------------------------------------------------------------
# Phase 2 — AI Computer Vision Quality Inspection
# ---------------------------------------------------------------------------

# "simulation" is the only mode implemented in Phase 2 (see backend/app/vision/).
# The abstraction is designed so a real provider can be added later without
# touching callers — see VisionService / VisionProvider.
VISION_MODE = os.environ.get("VISION_MODE", "simulation")
VISION_MODEL_VERSION = "vision-sim-v0.1"

IMAGE_STORAGE_DIR = os.environ.get(
    "IMAGE_STORAGE_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "images"),
)
IMAGE_MAX_SIZE_BYTES = 8 * 1024 * 1024  # 8 MB
ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}

# Quality Score (0-100) bands, purely descriptive (Excellent/Good/etc. labels).
QUALITY_SCORE_BANDS = {
    "EXCELLENT": (90, 100),
    "GOOD": (75, 89),
    "REVIEW": (60, 74),
    "POOR": (0, 59),
}

# Decision-engine thresholds — separate from the vision model itself.
VISION_DECISION_THRESHOLDS = {
    "pass_min_score": 75,
    "review_min_score": 60,
    # below review_min_score -> REJECT on score alone, regardless of defects
}

# Image quality validation thresholds (computed from real pixel data — see vision/quality.py).
IMAGE_QUALITY_THRESHOLDS = {
    "min_brightness": 35,       # 0-255 mean luminance; below this = "too dark"
    "max_brightness": 245,      # above this = blown out / product not visible
    "min_sharpness": 25,        # Laplacian-variance edge-energy proxy; below this = "too blurry"
    "min_width_px": 200,
    "min_height_px": 200,
}

# Risk-based inspection eligibility. "required_fragility"/"recommended_fragility"
# apply to the produce defect group (glass/packaged-goods groups use order-risk-only
# rules below, since packaging-damage risk isn't captured by the fragility score).
INSPECTION_RULES = {
    "LOW": {"produce_required": None, "produce_recommended": None, "structural_required": False},
    "MEDIUM": {"produce_required": None, "produce_recommended": 50, "structural_required": False},
    "HIGH": {"produce_required": 40, "produce_recommended": 20, "structural_required": True},
    "CRITICAL": {"produce_required": 0, "produce_recommended": 0, "structural_required": True},
}

# CRITICAL-risk orders route every inspected item to mandatory human review,
# even when the AI decision is PASS (see services/inspection logic).
MANDATORY_HUMAN_REVIEW_RISK_LEVELS = {"CRITICAL"}

# Repeated-rejection escalation (section 18 of the brief).
MAX_REPLACEMENT_ATTEMPTS_BEFORE_ESCALATION = 3


def quality_band_for_score(score: float) -> str:
    score = max(0, min(100, round(score)))
    for band, (low, high) in QUALITY_SCORE_BANDS.items():
        if low <= score <= high:
            return band
    return "POOR"
