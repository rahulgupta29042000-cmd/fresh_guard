"""Risk-based visual inspection eligibility — this is what keeps Phase 2
from inspecting every SKU automatically. Reuses the Phase 1 order risk
level (and the same category logic recommendations.py already uses) to
decide, per order item, whether AI inspection is required, recommended,
or not applicable.
"""
from .. import config
from . import categories

NONE = "none"
RECOMMENDED = "recommended"
REQUIRED = "required"


def compute_inspection_requirement(risk_level: str, category: str, packaging_type: str, fragility_score: float) -> str:
    group = categories.defect_group_for_product(category, packaging_type)
    if group == categories.NOT_INSPECTABLE:
        return NONE

    rules = config.INSPECTION_RULES.get(risk_level, config.INSPECTION_RULES["LOW"])

    if group == categories.PRODUCE:
        required_th = rules["produce_required"]
        recommended_th = rules["produce_recommended"]
        if required_th is not None and fragility_score >= required_th:
            return REQUIRED
        if recommended_th is not None and fragility_score >= recommended_th:
            return RECOMMENDED
        return NONE

    # Fragile-glass / packaged-goods: packaging-damage risk isn't captured by
    # fragility_score, so eligibility here is driven purely by order risk.
    if rules["structural_required"]:
        return REQUIRED
    if risk_level == "MEDIUM":
        return RECOMMENDED
    return NONE


def is_mandatory_human_review(risk_level: str) -> bool:
    return risk_level in config.MANDATORY_HUMAN_REVIEW_RISK_LEVELS
