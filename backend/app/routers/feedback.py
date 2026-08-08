from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/orders", tags=["feedback"])


def _load(db: Session, order_id: int) -> models.Order:
    order = (
        db.query(models.Order)
        .options(joinedload(models.Order.feedback), joinedload(models.Order.inspections))
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
        "flagged_as_possible_ai_miss": fb.flagged_as_possible_ai_miss,
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

    # Phase 2 <-> Phase 1 feedback loop: a damage complaint on an order where
    # every inspected item was accepted (by AI or human) is a candidate false
    # negative for the vision model — surfaced in analytics, not auto-acted on.
    accepted_inspections = [
        i for i in order.inspections if i.human_decision == "ACCEPT" or (i.ai_decision == "PASS" and i.human_decision is None)
    ]
    flagged = payload.issue_type != "none" and len(accepted_inspections) > 0

    fb = models.Feedback(
        order_id=order.id,
        rating=payload.rating,
        issue_type=payload.issue_type,
        comments=payload.comments,
        flagged_as_possible_ai_miss=flagged,
    )
    db.add(fb)
    order.status = "FEEDBACK_RECEIVED"
    db.commit()
    db.refresh(fb)
    return _feedback_out(fb)
