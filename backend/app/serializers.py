import json

from . import models


def order_item_to_risk_input(order_item: models.OrderItem) -> dict:
    p = order_item.product
    return {
        "name": p.name,
        "category": p.category,
        "fragility_score": p.fragility_score,
        "temperature_sensitive": p.temperature_sensitive,
        "weight_kg": p.weight_kg,
        "historical_damage_rate": p.historical_damage_rate,
        "quantity": order_item.quantity,
    }


def order_items_risk_input(order: models.Order) -> list:
    return [order_item_to_risk_input(oi) for oi in order.items]


def order_to_out(order: models.Order) -> dict:
    return {
        "id": order.id,
        "order_code": order.order_code,
        "customer_name": order.customer.name if order.customer else "",
        "warehouse_id": order.warehouse_id,
        "warehouse_name": order.warehouse.name if order.warehouse else "",
        "picker_id": order.picker_id,
        "rider_id": order.rider_id,
        "order_time": order.order_time,
        "total_weight": order.total_weight,
        "distance_km": order.distance_km,
        "status": order.status,
        "risk_score": order.risk_score,
        "risk_level": order.risk_level,
        "item_count": sum(i.quantity for i in order.items),
    }


def order_item_to_out(order_item: models.OrderItem) -> dict:
    from .config import risk_level_for_score  # noqa: F401  (kept local to avoid unused import warnings)

    p = order_item.product
    item_product_risk = round(
        min(100.0, 0.4 * p.fragility_score + 0.3 * p.fragility_score * 0.5 + p.historical_damage_rate * 100 * 0.3),
        1,
    )
    return {
        "id": order_item.id,
        "product": {
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "emoji": p.emoji,
            "weight_kg": p.weight_kg,
            "fragility_score": p.fragility_score,
            "temperature_sensitive": p.temperature_sensitive,
            "packaging_type": p.packaging_type,
            "historical_damage_rate": p.historical_damage_rate,
        },
        "quantity": order_item.quantity,
        "picked": order_item.picked,
        "damaged_reported": order_item.damaged_reported,
        "damage_note": order_item.damage_note,
        "product_risk": item_product_risk,
    }


def latest_risk_to_out(prediction: models.RiskPrediction, recommendations: list) -> dict:
    return {
        "riskScore": prediction.risk_score,
        "riskLevel": prediction.risk_level,
        "modelVersion": prediction.model_version,
        "predictionSource": prediction.prediction_source,
        "componentScores": json.loads(prediction.component_scores),
        "riskFactors": json.loads(prediction.risk_factors),
        "recommendations": [r.instruction for r in recommendations],
    }


def order_to_detail(order: models.Order, risk_out: dict = None) -> dict:
    out = order_to_out(order)
    out["items"] = [order_item_to_out(oi) for oi in order.items]
    out["risk"] = risk_out
    return out


def recommendation_to_out(rec: models.Recommendation) -> dict:
    return {
        "id": rec.id,
        "type": rec.type,
        "instruction": rec.instruction,
        "priority": rec.priority,
        "completed": rec.completed,
    }
