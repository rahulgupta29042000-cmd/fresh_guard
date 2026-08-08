from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/orders", tags=["feedback"])


def _load(db: Session, order_id: int) -> models.Order:
    order = (
        db.query(models.Order)
        .options(joinedload(models.Order.feedback))
        .filter(models.Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return order


def _feedback_out(fb: models.Feedback) -> dict:
    return {
        "order_id": fb.order_id,
        "rating": fb.rating,
        "issue_type": fb.issue_type,
        "comments": fb.comments,
        "created_at": fb.created_at,
    }


@router.get("/{order_id}/feedback")
def get_feedback(order_id: int, db: Session = Depends(get_db)):
    order = _load(db, order_id)
    if not order.feedback:
        return None
    return _feedback_out(order.feedback)


@router.post("/{order_id}/feedback")
def submit_feedback(order_id: int, payload: schemas.FeedbackCreate, db: Session = Depends(get_db)):
    order = _load(db, order_id)
    if order.feedback:
        raise HTTPException(status_code=409, detail="Feedback already submitted for this order")

    fb = models.Feedback(
        order_id=order.id,
        rating=payload.rating,
        issue_type=payload.issue_type,
        comments=payload.comments,
    )
    db.add(fb)
    order.status = "FEEDBACK_RECEIVED"
    db.commit()
    db.refresh(fb)
    return _feedback_out(fb)
