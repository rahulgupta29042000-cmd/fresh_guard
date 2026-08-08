import datetime
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas, services
from ..database import get_db

router = APIRouter(prefix="/api/orders", tags=["delivery"])


def _load(db: Session, order_id: int) -> models.Order:
    order = (
        db.query(models.Order)
        .options(joinedload(models.Order.items).joinedload(models.OrderItem.product), joinedload(models.Order.delivery_instruction))
        .filter(models.Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return order


def _instruction_out(di: models.DeliveryInstruction) -> dict:
    return {
        "order_id": di.order_id,
        "instructions": json.loads(di.instructions_json),
        "fragile_item_count": di.fragile_item_count,
        "temperature_sensitive_item_count": di.temperature_sensitive_item_count,
        "accepted": di.accepted,
        "accepted_at": di.accepted_at,
    }


@router.get("/{order_id}/delivery")
def get_delivery_instructions(order_id: int, db: Session = Depends(get_db)):
    order = _load(db, order_id)
    di = services.get_or_create_delivery_instruction(db, order)
    return _instruction_out(di)


@router.post("/{order_id}/delivery")
def delivery_action(order_id: int, payload: schemas.DeliveryAction, db: Session = Depends(get_db)):
    order = _load(db, order_id)
    di = services.get_or_create_delivery_instruction(db, order)

    if payload.action == "accept_instructions":
        di.accepted = True
        di.accepted_at = datetime.datetime.utcnow()
        order.status = "DISPATCHED"
        order.dispatched_at = datetime.datetime.utcnow()

    elif payload.action == "mark_delivered":
        order.status = "DELIVERED"
        order.delivered_at = datetime.datetime.utcnow()

    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {payload.action}")

    db.commit()
    db.refresh(di)
    return _instruction_out(di)
