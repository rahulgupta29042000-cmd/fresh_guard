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
        "requires_inspection": order_item.requires_inspection,
        "quality_check_status": order_item.quality_check_status,
        "replaced": order_item.replaced,
        "replaced_by_item_id": order_item.replaced_by_item_id,
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


# ---------------------------------------------------------------------------
# Phase 2 — AI Computer Vision Quality Inspection
# ---------------------------------------------------------------------------


def image_to_out(image: models.InspectionImage) -> dict:
    return {
        "id": image.id,
        "url": f"/api/images/{image.id}/file",
        "imageQuality": {
            "score": image.image_quality_score,
            "status": image.image_quality_status,
            "issues": json.loads(image.image_quality_issues) if image.image_quality_issues else [],
        },
        "createdAt": image.created_at,
    }


def defect_to_out(defect: models.InspectionDefect) -> dict:
    return {
        "type": defect.defect_type,
        "confidence": defect.confidence,
        "severity": defect.severity,
        "description": defect.description,
    }


def inspection_to_out(inspection: models.Inspection) -> dict:
    p = inspection.product
    return {
        "inspectionId": inspection.id,
        "orderId": inspection.order_id,
        "orderCode": inspection.order.order_code if inspection.order else None,
        "orderItemId": inspection.order_item_id,
        "product": {"id": p.id, "name": p.name, "emoji": p.emoji, "category": p.category},
        "attemptNumber": inspection.attempt_number,
        "qualityScore": inspection.quality_score,
        "inspectionStatus": inspection.inspection_status,
        "aiDecision": inspection.ai_decision,
        "humanDecision": inspection.human_decision,
        "mandatoryHumanReview": inspection.mandatory_human_review,
        "modelVersion": inspection.model_version,
        "visionMode": inspection.vision_mode,
        "inspectionTimeMs": inspection.inspection_time_ms,
        "image": image_to_out(inspection.image) if inspection.image else None,
        "defects": [defect_to_out(d) for d in inspection.defects],
        "reviewedAt": inspection.reviewed_at,
        "reviewedBy": inspection.reviewed_by.name if inspection.reviewed_by else None,
        "createdAt": inspection.created_at,
    }
