import json
import time

from fastapi import HTTPException
from sqlalchemy.orm import Session

from . import config, models, serializers
from .vision import eligibility
from .vision.service import VisionAnalysisUnavailable, get_vision_service
from .vision.storage import get_storage


def get_inspection_or_404(db: Session, inspection_id: int) -> models.Inspection:
    inspection = db.get(models.Inspection, inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail=f"Inspection {inspection_id} not found")
    return inspection


def get_order_item_or_404(db: Session, order_item_id: int) -> models.OrderItem:
    item = db.get(models.OrderItem, order_item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Order item {order_item_id} not found")
    return item


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------


def save_uploaded_image(db: Session, file_bytes: bytes, content_type: str) -> models.InspectionImage:
    if len(file_bytes) > config.IMAGE_MAX_SIZE_BYTES:
        raise HTTPException(status_code=400, detail=f"Image exceeds {config.IMAGE_MAX_SIZE_BYTES // (1024 * 1024)}MB limit")
    if content_type not in config.ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported image type: {content_type}")

    vision = get_vision_service()
    try:
        quality = vision.validate_image(file_bytes)
    except Exception:
        raise HTTPException(status_code=400, detail="Unable to read image — file may be corrupted or not an image")

    extension = "jpg" if content_type == "image/jpeg" else content_type.split("/")[-1]
    file_path = get_storage().save(file_bytes, extension)

    image = models.InspectionImage(
        file_path=file_path,
        content_type=content_type,
        size_bytes=len(file_bytes),
        image_quality_score=quality["score"],
        image_quality_status=quality["status"],
        image_quality_issues=json.dumps(quality["issues"]),
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


def save_sample_image(db: Session, sample_key: str) -> models.InspectionImage:
    import os

    samples_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "images", "samples"
    )
    manifest_path = os.path.join(samples_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        raise HTTPException(status_code=500, detail="Sample image manifest not found — run data/seed/generate_sample_images.py")
    manifest = json.load(open(manifest_path))
    entry = next((m for m in manifest if m["key"] == sample_key), None)
    if not entry:
        raise HTTPException(status_code=400, detail=f"Unknown sample_key: {sample_key}")

    with open(os.path.join(samples_dir, entry["file"]), "rb") as f:
        file_bytes = f.read()
    return save_uploaded_image(db, file_bytes, "image/jpeg")


def list_samples() -> list:
    import os

    manifest_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "images", "samples", "manifest.json"
    )
    if not os.path.exists(manifest_path):
        return []
    return json.load(open(manifest_path))


# ---------------------------------------------------------------------------
# Inspections
# ---------------------------------------------------------------------------


def create_inspection(db: Session, order_id: int, order_item_id: int, image_id: int = None) -> models.Inspection:
    order = db.get(models.Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    item = get_order_item_or_404(db, order_item_id)
    if item.order_id != order_id:
        raise HTTPException(status_code=400, detail="Order item does not belong to this order")

    prior_attempts = db.query(models.Inspection).filter(models.Inspection.order_item_id == order_item_id).count()

    inspection = models.Inspection(
        order_id=order_id,
        order_item_id=order_item_id,
        product_id=item.product_id,
        attempt_number=prior_attempts + 1,
        inspection_status="PENDING",
        mandatory_human_review=eligibility.is_mandatory_human_review(order.risk_level or "LOW"),
    )
    db.add(inspection)
    db.flush()

    if image_id:
        image = db.get(models.InspectionImage, image_id)
        if not image:
            raise HTTPException(status_code=400, detail=f"Image {image_id} not found")
        image.inspection_id = inspection.id

    item.quality_check_status = "PENDING"
    db.commit()
    db.refresh(inspection)
    return inspection


def attach_image(db: Session, inspection: models.Inspection, image_id: int) -> models.Inspection:
    image = db.get(models.InspectionImage, image_id)
    if not image:
        raise HTTPException(status_code=400, detail=f"Image {image_id} not found")
    image.inspection_id = inspection.id
    db.commit()
    db.refresh(inspection)
    return inspection


def analyze_inspection(db: Session, inspection: models.Inspection) -> models.Inspection:
    image = inspection.image
    if not image:
        raise HTTPException(status_code=400, detail="No image attached to this inspection yet")
    if image.image_quality_status == "poor":
        raise HTTPException(
            status_code=422,
            detail="Image quality insufficient. Please improve lighting, move the product closer, keep it centered, and retake the image.",
        )

    product = inspection.product
    vision = get_vision_service()
    storage = get_storage()

    started = time.monotonic()
    try:
        image_bytes = storage.read(image.file_path)
        result = vision.analyze(image_bytes, product)
    except VisionAnalysisUnavailable:
        inspection.inspection_status = "PENDING"
        db.commit()
        raise HTTPException(
            status_code=503,
            detail="AI inspection temporarily unavailable. Continue with manual quality inspection.",
        )
    elapsed_ms = int((time.monotonic() - started) * 1000)

    ai_status = result["status"]
    final_status = ai_status
    if inspection.mandatory_human_review and ai_status == "PASS":
        # CRITICAL-risk orders: even an AI PASS still needs a human look.
        final_status = "REVIEW"

    inspection.quality_score = result["quality_score"]
    inspection.ai_decision = ai_status
    inspection.inspection_status = final_status
    inspection.model_version = result["model_version"]
    inspection.vision_mode = result["vision_mode"]
    inspection.inspection_time_ms = elapsed_ms

    for defect in result["defects"]:
        db.add(
            models.InspectionDefect(
                inspection_id=inspection.id,
                defect_type=defect["type"],
                confidence=defect["confidence"],
                severity=defect["severity"],
                description=defect.get("label"),
            )
        )

    max_confidence = max((d["confidence"] for d in result["defects"]), default=None)
    db.add(
        models.ModelPrediction(
            inspection_id=inspection.id,
            model_version=result["model_version"],
            prediction=ai_status,
            confidence=max_confidence,
            raw_result=json.dumps(result["raw"]),
        )
    )

    db.commit()
    db.refresh(inspection)
    return inspection


def _apply_human_decision(db: Session, inspection: models.Inspection, decision: str, reviewer_id: int = None) -> models.Inspection:
    import datetime

    inspection.human_decision = decision
    inspection.reviewed_at = datetime.datetime.utcnow()
    inspection.reviewed_by_id = reviewer_id

    item = inspection.order_item
    item.quality_check_status = "PASSED" if decision == "ACCEPT" else "FAILED"

    db.commit()
    db.refresh(inspection)
    return inspection


def accept_inspection(db: Session, inspection: models.Inspection) -> models.Inspection:
    return _apply_human_decision(db, inspection, "ACCEPT")


def reject_inspection(db: Session, inspection: models.Inspection) -> models.Inspection:
    return _apply_human_decision(db, inspection, "REJECT")


def reinspect(db: Session, inspection: models.Inspection) -> models.Inspection:
    """Rescan the SAME physical item — e.g. after a poor-quality photo.
    (Use replace_item instead when swapping in a different physical unit.)"""
    return create_inspection(db, inspection.order_id, inspection.order_item_id, image_id=None)


def count_rejections_for_category(db: Session, order_id: int, category: str) -> int:
    inspections = (
        db.query(models.Inspection)
        .join(models.Product, models.Inspection.product_id == models.Product.id)
        .filter(
            models.Inspection.order_id == order_id,
            models.Product.category == category,
            models.Inspection.human_decision == "REJECT",
        )
        .count()
    )
    return inspections


def replace_item(db: Session, inspection: models.Inspection, replacement_product_id: int, reason: str = None) -> dict:
    original_item = inspection.order_item
    replacement_product = db.get(models.Product, replacement_product_id)
    if not replacement_product:
        raise HTTPException(status_code=400, detail=f"Product {replacement_product_id} not found")

    new_item = models.OrderItem(
        order_id=original_item.order_id,
        product_id=replacement_product_id,
        quantity=original_item.quantity,
        requires_inspection=original_item.requires_inspection,
        quality_check_status="PENDING",
        picked=original_item.picked,
    )
    db.add(new_item)
    db.flush()

    original_item.replaced = True
    original_item.replaced_by_item_id = new_item.id

    db.add(
        models.ReplacementEvent(
            order_item_id=new_item.id,
            original_product_id=original_item.product_id,
            replacement_product_id=replacement_product_id,
            reason=reason or "Failed AI quality inspection",
            inspection_id=inspection.id,
        )
    )
    db.commit()
    db.refresh(new_item)

    rejection_count = count_rejections_for_category(db, original_item.order_id, inspection.product.category)
    escalate = rejection_count >= config.MAX_REPLACEMENT_ATTEMPTS_BEFORE_ESCALATION
    if escalate:
        db.add(
            models.Recommendation(
                order_id=original_item.order_id,
                type="manager_alert",
                instruction=(
                    f"{rejection_count} failed inspections for {inspection.product.category} in this order — "
                    "escalate to warehouse/QC manager."
                ),
                priority="critical",
            )
        )
        db.commit()

    new_inspection = create_inspection(db, original_item.order_id, new_item.id)

    return {
        "newOrderItem": serializers.order_item_to_out(new_item),
        "newInspectionId": new_inspection.id,
        "escalate": escalate,
        "rejectionCount": rejection_count,
    }


def get_review_queue(db: Session) -> list:
    return (
        db.query(models.Inspection)
        .filter(models.Inspection.inspection_status == "REVIEW", models.Inspection.human_decision.is_(None))
        .order_by(models.Inspection.created_at.asc())
        .all()
    )
