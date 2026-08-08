import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from .. import inspection_analytics, models
from ..database import get_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

DELIVERED_STATUSES = ("DELIVERED", "FEEDBACK_RECEIVED")
REFUND_ISSUE_TYPES = ("broken_item", "crushed_packaging", "spoiled_product")


def _damage_free_rate(feedbacks) -> float:
    if not feedbacks:
        return 100.0
    no_issue = sum(1 for f in feedbacks if f.issue_type == "none")
    return round(no_issue / len(feedbacks) * 100, 1)


@router.get("")
def get_dashboard(db: Session = Depends(get_db)):
    now = datetime.datetime.utcnow()
    today = now.date()
    last_7 = now - datetime.timedelta(days=7)
    prev_7 = now - datetime.timedelta(days=14)

    all_feedback = (
        db.query(models.Feedback).options(joinedload(models.Feedback.order)).join(models.Order).all()
    )
    recent_feedback = [f for f in all_feedback if f.order.order_time >= last_7]
    prior_feedback = [f for f in all_feedback if prev_7 <= f.order.order_time < last_7]

    damage_free_rate = _damage_free_rate(all_feedback)
    recent_rate = _damage_free_rate(recent_feedback)
    prior_rate = _damage_free_rate(prior_feedback)
    change = round(recent_rate - prior_rate, 1) if prior_feedback else 0.0

    orders_today = db.query(models.Order).filter(models.Order.order_time >= datetime.datetime.combine(today, datetime.time.min)).count()
    high_risk_today = (
        db.query(models.Order)
        .filter(
            models.Order.order_time >= datetime.datetime.combine(today, datetime.time.min),
            models.Order.risk_level.in_(("HIGH", "CRITICAL")),
        )
        .count()
    )

    refund_worthy = sum(1 for f in all_feedback if f.issue_type in REFUND_ISSUE_TYPES)
    refund_rate = round(refund_worthy / len(all_feedback) * 100, 1) if all_feedback else 0.0

    kpis = {
        "damage_free_rate": damage_free_rate,
        "damage_free_rate_change": change,
        "orders_today": orders_today,
        "high_risk_orders_today": high_risk_today,
        "damage_rate": round(100 - damage_free_rate, 1),
        "refund_rate": refund_rate,
    }

    risk_rows = db.query(models.Order.risk_level, models.Order.id).filter(models.Order.risk_level.isnot(None)).all()
    risk_distribution = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    for level, _ in risk_rows:
        if level in risk_distribution:
            risk_distribution[level] += 1

    damaged_items = (
        db.query(models.OrderItem)
        .options(joinedload(models.OrderItem.product))
        .filter(models.OrderItem.damaged_reported.is_(True))
        .all()
    )
    category_counts: dict = {}
    sku_counts: dict = {}
    for item in damaged_items:
        category_counts[item.product.category] = category_counts.get(item.product.category, 0) + 1
        sku_counts[item.product.name] = sku_counts.get(item.product.name, 0) + 1

    top_damaged_categories = [
        {"category": k, "count": v} for k, v in sorted(category_counts.items(), key=lambda kv: -kv[1])[:5]
    ]
    top_problematic_skus = [
        {"product": k, "count": v} for k, v in sorted(sku_counts.items(), key=lambda kv: -kv[1])[:5]
    ]

    warehouses = db.query(models.Warehouse).all()
    warehouse_comparison = []
    for w in warehouses:
        w_orders = db.query(models.Order).filter(models.Order.warehouse_id == w.id).count()
        w_feedback = [f for f in all_feedback if f.order.warehouse_id == w.id]
        warehouse_comparison.append(
            {
                "warehouse": w.name,
                "orders": w_orders,
                "damage_free_rate": _damage_free_rate(w_feedback),
                "current_load": w.current_load,
                "capacity": w.capacity,
            }
        )

    return {
        "kpis": kpis,
        "risk_distribution": risk_distribution,
        "top_damaged_categories": top_damaged_categories,
        "top_problematic_skus": top_problematic_skus,
        "warehouse_comparison": warehouse_comparison,
        "ai_inspection": inspection_analytics.summary(db),
    }
