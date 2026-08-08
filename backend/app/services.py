import json

from fastapi import HTTPException
from sqlalchemy.orm import Session

from . import models, recommendations, risk_engine, serializers


def get_order_or_404(db: Session, order_id: int) -> models.Order:
    order = db.get(models.Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return order


def compute_total_weight(order: models.Order) -> float:
    return round(sum(oi.product.weight_kg * oi.quantity for oi in order.items), 2)


def run_risk_assessment(db: Session, order: models.Order) -> dict:
    """Runs the risk engine, persists a RiskPrediction row, updates the
    order's latest score/level, and regenerates recommendations.

    If the risk engine raises for any reason, the order is NOT blocked —
    per the Phase 1 fallback requirement — it just proceeds with no risk
    data and the caller/UI shows "AI risk assessment unavailable."
    """
    items = serializers.order_items_risk_input(order)

    try:
        result = risk_engine.assess_risk(order, items, order.warehouse, order.picker, order.rider)
    except Exception:
        return None

    prediction = models.RiskPrediction(
        order_id=order.id,
        risk_score=result["risk_score"],
        risk_level=result["risk_level"],
        risk_factors=json.dumps(result["risk_factors"]),
        component_scores=json.dumps(result["component_scores"]),
        model_version=result["model_version"],
        prediction_source=result["prediction_source"],
    )
    db.add(prediction)

    order.risk_score = result["risk_score"]
    order.risk_level = result["risk_level"]
    if order.status == "CREATED":
        order.status = "RISK_ASSESSED"

    for existing in list(order.recommendations):
        db.delete(existing)

    rec_items = [
        {
            "name": oi.product.name,
            "category": oi.product.category,
            "fragility_score": oi.product.fragility_score,
            "temperature_sensitive": oi.product.temperature_sensitive,
            "weight_kg": oi.product.weight_kg,
        }
        for oi in order.items
    ]
    rec_dicts = recommendations.generate_recommendations(result["risk_level"], rec_items, order.distance_km)
    for rec in rec_dicts:
        db.add(models.Recommendation(order_id=order.id, type=rec["type"], instruction=rec["instruction"], priority=rec["priority"]))

    db.commit()
    db.refresh(order)

    return serializers.latest_risk_to_out(prediction, order.recommendations)


def latest_risk_out(order: models.Order) -> dict:
    if not order.risk_predictions:
        return None
    latest = sorted(order.risk_predictions, key=lambda p: p.created_at)[-1]
    return serializers.latest_risk_to_out(latest, order.recommendations)


FRAGILE_CATEGORY_BAG = "FRAGILE"
PRODUCE_BAG = "PRODUCE"
COLD_BAG = "COLD / TEMPERATURE-PROTECTED"
LIGHTWEIGHT_BAG = "LIGHTWEIGHT"
GENERAL_BAG = "GENERAL"


def build_packing_plan(order: models.Order) -> list:
    bags = {FRAGILE_CATEGORY_BAG: [], COLD_BAG: [], PRODUCE_BAG: [], LIGHTWEIGHT_BAG: [], GENERAL_BAG: []}
    for oi in order.items:
        p = oi.product
        entry = {"order_item_id": oi.id, "name": p.name}
        if p.fragility_score >= 65:
            bags[FRAGILE_CATEGORY_BAG].append(entry)
        elif p.temperature_sensitive:
            bags[COLD_BAG].append(entry)
        elif p.category == "produce":
            bags[PRODUCE_BAG].append(entry)
        elif p.weight_kg < 0.4:
            bags[LIGHTWEIGHT_BAG].append(entry)
        else:
            bags[GENERAL_BAG].append(entry)

    plan = []
    for bag_name, items in bags.items():
        if items:
            plan.append({"bag_name": bag_name, "category": bag_name, "items": items})
    return plan


def get_or_create_packing_plan(db: Session, order: models.Order) -> models.PackingPlan:
    if order.packing_plan:
        return order.packing_plan
    plan = models.PackingPlan(order_id=order.id, plan_json=json.dumps(build_packing_plan(order)), status="proposed")
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def build_delivery_instructions(order: models.Order) -> list:
    instructions = []
    fragile_count = sum(oi.quantity for oi in order.items if oi.product.fragility_score >= 65)
    temp_count = sum(oi.quantity for oi in order.items if oi.product.temperature_sensitive)

    if fragile_count:
        instructions += ["Keep upright", "Avoid placing heavy items on top"]
    if temp_count:
        instructions.append("Keep temperature-sensitive item(s) protected")
    if order.risk_level in ("HIGH", "CRITICAL"):
        instructions.append("Deliver promptly — minimize transit time")
    if not instructions:
        instructions.append("Standard handling — no special precautions required")

    return instructions, fragile_count, temp_count


def get_or_create_delivery_instruction(db: Session, order: models.Order) -> models.DeliveryInstruction:
    if order.delivery_instruction:
        return order.delivery_instruction
    instructions, fragile_count, temp_count = build_delivery_instructions(order)
    di = models.DeliveryInstruction(
        order_id=order.id,
        instructions_json=json.dumps(instructions),
        fragile_item_count=fragile_count,
        temperature_sensitive_item_count=temp_count,
    )
    db.add(di)
    db.commit()
    db.refresh(di)
    return di
