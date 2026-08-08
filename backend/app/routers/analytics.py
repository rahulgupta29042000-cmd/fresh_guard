import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from .. import inspection_analytics, models
from ..database import get_db

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


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
