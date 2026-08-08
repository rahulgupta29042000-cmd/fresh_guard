from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from .. import inspection_service, models, schemas, serializers
from ..database import get_db

router = APIRouter(prefix="/api/inspections", tags=["inspections"])


def _query(db: Session):
    return db.query(models.Inspection).options(
        joinedload(models.Inspection.product),
        joinedload(models.Inspection.order),
        joinedload(models.Inspection.image),
        joinedload(models.Inspection.defects),
        joinedload(models.Inspection.reviewed_by),
    )


@router.post("")
def create_inspection(payload: schemas.InspectionCreate, db: Session = Depends(get_db)):
    inspection = inspection_service.create_inspection(db, payload.order_id, payload.order_item_id, payload.image_id)
    return serializers.inspection_to_out(inspection)


@router.get("")
def list_inspections(
    order_id: Optional[int] = Query(default=None),
    order_item_id: Optional[int] = Query(default=None),
    product_id: Optional[int] = Query(default=None),
    defect_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None, description="PENDING | PASS | REVIEW | REJECT"),
    warehouse_id: Optional[int] = Query(default=None),
    min_confidence: Optional[float] = Query(default=None),
    date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    limit: int = Query(default=200, le=1000),
    db: Session = Depends(get_db),
):
    q = _query(db)
    if order_id:
        q = q.filter(models.Inspection.order_id == order_id)
    if order_item_id:
        q = q.filter(models.Inspection.order_item_id == order_item_id)
    if product_id:
        q = q.filter(models.Inspection.product_id == product_id)
    if status:
        q = q.filter(models.Inspection.inspection_status == status.upper())
    if warehouse_id:
        q = q.join(models.Order, models.Inspection.order_id == models.Order.id).filter(models.Order.warehouse_id == warehouse_id)
    if defect_type or min_confidence is not None:
        q = q.join(models.InspectionDefect, models.InspectionDefect.inspection_id == models.Inspection.id)
        if defect_type:
            q = q.filter(models.InspectionDefect.defect_type == defect_type)
        if min_confidence is not None:
            q = q.filter(models.InspectionDefect.confidence >= min_confidence)
    if date:
        import datetime

        try:
            day = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
        q = q.filter(
            models.Inspection.created_at >= datetime.datetime.combine(day, datetime.time.min),
            models.Inspection.created_at <= datetime.datetime.combine(day, datetime.time.max),
        )

    inspections = q.order_by(models.Inspection.created_at.desc()).limit(limit).all()
    return [serializers.inspection_to_out(i) for i in inspections]


@router.get("/{inspection_id}")
def get_inspection(inspection_id: int, db: Session = Depends(get_db)):
    inspection = _query(db).filter(models.Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=404, detail=f"Inspection {inspection_id} not found")
    return serializers.inspection_to_out(inspection)


@router.post("/{inspection_id}/image")
def attach_image(inspection_id: int, payload: dict, db: Session = Depends(get_db)):
    inspection = inspection_service.get_inspection_or_404(db, inspection_id)
    image_id = payload.get("image_id")
    if not image_id:
        raise HTTPException(status_code=400, detail="image_id is required")
    inspection = inspection_service.attach_image(db, inspection, image_id)
    return serializers.inspection_to_out(inspection)


@router.post("/{inspection_id}/analyze")
def analyze(inspection_id: int, db: Session = Depends(get_db)):
    inspection = inspection_service.get_inspection_or_404(db, inspection_id)
    inspection = inspection_service.analyze_inspection(db, inspection)
    return serializers.inspection_to_out(inspection)


@router.post("/{inspection_id}/accept")
def accept(inspection_id: int, payload: schemas.InspectionHumanDecision = None, db: Session = Depends(get_db)):
    inspection = inspection_service.get_inspection_or_404(db, inspection_id)
    inspection = inspection_service.accept_inspection(db, inspection)
    return serializers.inspection_to_out(inspection)


@router.post("/{inspection_id}/reject")
def reject(inspection_id: int, payload: schemas.InspectionHumanDecision = None, db: Session = Depends(get_db)):
    inspection = inspection_service.get_inspection_or_404(db, inspection_id)
    inspection = inspection_service.reject_inspection(db, inspection)
    return serializers.inspection_to_out(inspection)


@router.post("/{inspection_id}/review")
def mark_review(inspection_id: int, db: Session = Depends(get_db)):
    inspection = inspection_service.get_inspection_or_404(db, inspection_id)
    inspection.inspection_status = "REVIEW"
    db.commit()
    db.refresh(inspection)
    return serializers.inspection_to_out(inspection)


@router.post("/{inspection_id}/reinspect")
def reinspect(inspection_id: int, db: Session = Depends(get_db)):
    inspection = inspection_service.get_inspection_or_404(db, inspection_id)
    new_inspection = inspection_service.reinspect(db, inspection)
    return serializers.inspection_to_out(new_inspection)


@router.post("/{inspection_id}/replace")
def replace(inspection_id: int, payload: schemas.ReplaceRequest, db: Session = Depends(get_db)):
    inspection = inspection_service.get_inspection_or_404(db, inspection_id)
    if inspection.human_decision != "REJECT":
        raise HTTPException(status_code=400, detail="Can only replace an item whose inspection was rejected")
    return inspection_service.replace_item(db, inspection, payload.replacement_product_id, payload.reason)
