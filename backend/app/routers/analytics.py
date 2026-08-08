import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from .. import inspection_analytics, models
from ..database import get_db

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

DELIVERED_STATUSES = ("DELIVERED", "FEEDBACK_RECEIVED")


@router.get("/inspections")
def inspection_analytics_endpoint(db: Session = Depends(get_db)):
    base = inspection_analytics.summary(db)
    inspections = db.query(models.Inspection).filter(models.Inspection.ai_decision.isnot(None)).all()
    reviewed = [i for i in inspections if i.human_decision is not None]

    transitions = {"PASS_to_REJECT": 0, "REJECT_to_ACCEPT": 0, "REVIEW_to_ACCEPT": 0, "REVIEW_to_REJECT": 0}
    for i in reviewed:
        if i.ai_decision == "PASS" and i.human_decision == "REJECT":
            transitions["PASS_to_REJECT"] += 1
        elif i.ai_decision == "REJECT" and i.human_decision == "ACCEPT":
            transitions["REJECT_to_ACCEPT"] += 1
        elif i.ai_decision == "REVIEW" and i.human_decision == "ACCEPT":
            transitions["REVIEW_to_ACCEPT"] += 1
        elif i.ai_decision == "REVIEW" and i.human_decision == "REJECT":
            transitions["REVIEW_to_REJECT"] += 1

    quality_scores = [i.quality_score for i in inspections if i.quality_score is not None]
    times = [i.inspection_time_ms for i in inspections if i.inspection_time_ms is not None]
    defect_counts: dict = {}
    for i in inspections:
        for d in i.defects:
            defect_counts[d.defect_type] = defect_counts.get(d.defect_type, 0) + 1
    most_common_defect = max(defect_counts.items(), key=lambda kv: kv[1])[0] if defect_counts else None

    return {
        "note": "Model performance on Phase 2 prototype/simulation data — see README for limitations.",
        **base,
        "reviewRate": round(base["review"] / base["inspected"] * 100, 1) if base["inspected"] else 0.0,
        "overrideTransitions": transitions,
        "defectsDetected": sum(defect_counts.values()),
        "mostCommonDefect": most_common_defect,
        "avgQualityScore": round(sum(quality_scores) / len(quality_scores), 1) if quality_scores else None,
        "avgInspectionTimeMs": round(sum(times) / len(times)) if times else None,
    }


@router.get("/defects")
def defect_analytics(db: Session = Depends(get_db)):
    defects = (
        db.query(models.InspectionDefect)
        .options(joinedload(models.InspectionDefect.inspection).joinedload(models.Inspection.product))
        .options(joinedload(models.InspectionDefect.inspection).joinedload(models.Inspection.order).joinedload(models.Order.warehouse))
        .all()
    )
    total = len(defects)

    def bucket(key_fn):
        counts: dict = {}
        for d in defects:
            key = key_fn(d)
            if key is None:
                continue
            counts[key] = counts.get(key, 0) + 1
        return sorted(
            [{"key": k, "count": v, "percent": round(v / total * 100, 1) if total else 0.0} for k, v in counts.items()],
            key=lambda x: -x["count"],
        )

    by_type = bucket(lambda d: d.defect_type)
    by_category = bucket(lambda d: d.inspection.product.category if d.inspection and d.inspection.product else None)
    by_sku = bucket(lambda d: d.inspection.product.name if d.inspection and d.inspection.product else None)
    by_warehouse = bucket(
        lambda d: d.inspection.order.warehouse.name if d.inspection and d.inspection.order and d.inspection.order.warehouse else None
    )
    by_day = bucket(lambda d: d.inspection.created_at.date().isoformat() if d.inspection else None)

    return {
        "totalDefects": total,
        "byType": by_type[:10],
        "byCategory": by_category[:10],
        "bySku": by_sku[:10],
        "byWarehouse": by_warehouse,
        "byDay": sorted(by_day, key=lambda x: x["key"]),
    }


@router.get("/overview")
def analytics_overview(db: Session = Depends(get_db)):
    """Single-fetch payload for the /analytics page: Quality, AI, Defects,
    and Operational sections (section 21/22 of the MVP brief)."""
    orders = db.query(models.Order).all()
    delivered_orders = [o for o in orders if o.status in DELIVERED_STATUSES]
    feedback = db.query(models.Feedback).options(joinedload(models.Feedback.order)).all()

    no_issue = sum(1 for f in feedback if f.issue_type == "none")
    damage_free_rate = round(no_issue / len(feedback) * 100, 1) if feedback else 100.0
    customer_issue_rate = round(100 - damage_free_rate, 1)

    inspections = db.query(models.Inspection).filter(models.Inspection.ai_decision.isnot(None)).all()
    ai = inspection_analytics.summary(db)

    replacement_events = db.query(models.ReplacementEvent).count()
    replacement_rate = round(replacement_events / len(inspections) * 100, 1) if inspections else 0.0

    risk_assessed_orders = [o for o in orders if o.risk_level]
    high_risk_orders = [o for o in risk_assessed_orders if o.risk_level in ("HIGH", "CRITICAL")]
    high_risk_order_rate = round(len(high_risk_orders) / len(risk_assessed_orders) * 100, 1) if risk_assessed_orders else 0.0

    times = [i.inspection_time_ms for i in inspections if i.inspection_time_ms is not None]
    avg_inspection_time_ms = round(sum(times) / len(times)) if times else None

    defect_counts: dict = {}
    for i in inspections:
        for d in i.defects:
            defect_counts[d.defect_type] = defect_counts.get(d.defect_type, 0) + 1
    defects_by_type = sorted(
        [{"key": k, "count": v} for k, v in defect_counts.items()], key=lambda x: -x["count"]
    )

    # Quality trend: damage-free rate per day, last 14 days with feedback.
    by_day: dict = {}
    for f in feedback:
        day = f.order.order_time.date().isoformat() if f.order else None
        if not day:
            continue
        by_day.setdefault(day, []).append(f.issue_type == "none")
    trend = [
        {"date": day, "damageFreeRate": round(sum(vals) / len(vals) * 100, 1), "orders": len(vals)}
        for day, vals in sorted(by_day.items())
    ][-14:]

    return {
        "note": "Prototype analytics based on simulated/demo data.",
        "quality": {
            "damageFreeRate": damage_free_rate,
            "customerIssueRate": customer_issue_rate,
            "rejectedProducts": ai["rejected"],
            "aiInspectionVolume": ai["inspected"],
            "deliveredOrders": len(delivered_orders),
        },
        "ai": {
            "pass": ai["passed"],
            "review": ai["review"],
            "reject": ai["rejected"],
            "humanOverrides": round(ai["humanOverrideRate"] * ai["humanReviewedCount"] / 100) if ai["humanReviewedCount"] else 0,
            "rejectRate": ai["rejectRate"],
            "humanOverrideRate": ai["humanOverrideRate"],
        },
        "defects": {"byType": defects_by_type[:10]},
        "operational": {
            "avgInspectionTimeMs": avg_inspection_time_ms,
            "replacementRate": replacement_rate,
            "highRiskOrderRate": high_risk_order_rate,
        },
        "qualityTrend": trend,
    }
