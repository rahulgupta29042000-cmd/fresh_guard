"""Shared AI-inspection KPI computation, used by both the dedicated
/api/analytics/inspections endpoint and the /api/dashboard summary block."""
from sqlalchemy.orm import Session

from . import models


def summary(db: Session) -> dict:
    inspections = db.query(models.Inspection).filter(models.Inspection.ai_decision.isnot(None)).all()
    inspected = len(inspections)
    passed = sum(1 for i in inspections if i.ai_decision == "PASS")
    review = sum(1 for i in inspections if i.ai_decision == "REVIEW")
    rejected = sum(1 for i in inspections if i.ai_decision == "REJECT")

    reviewed = [i for i in inspections if i.human_decision is not None]
    true_overrides = sum(
        1
        for i in reviewed
        if (i.ai_decision == "PASS" and i.human_decision == "REJECT")
        or (i.ai_decision == "REJECT" and i.human_decision == "ACCEPT")
    )

    return {
        "inspected": inspected,
        "passed": passed,
        "review": review,
        "rejected": rejected,
        "rejectRate": round(rejected / inspected * 100, 1) if inspected else 0.0,
        "humanReviewedCount": len(reviewed),
        "humanOverrideRate": round(true_overrides / len(reviewed) * 100, 1) if reviewed else 0.0,
    }
