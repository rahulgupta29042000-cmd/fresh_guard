import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas, serializers, services
from ..database import get_db

router = APIRouter(prefix="/api/orders", tags=["picking"])


def _load(db: Session, order_id: int) -> models.Order:
    order = (
        db.query(models.Order)
        .options(joinedload(models.Order.items).joinedload(models.OrderItem.product))
        .filter(models.Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return order


@router.post("/{order_id}/picking", response_model=schemas.OrderDetailOut)
def picking_action(order_id: int, payload: schemas.PickingAction, db: Session = Depends(get_db)):
    order = _load(db, order_id)

    if payload.action == "start":
        order.status = "PICKING"
        order.picking_started_at = datetime.datetime.utcnow()

    elif payload.action == "mark_item_picked":
        if payload.item_id is None:
            raise HTTPException(status_code=400, detail="item_id is required for mark_item_picked")
        item = next((i for i in order.items if i.id == payload.item_id), None)
        if not item:
            raise HTTPException(status_code=404, detail=f"Order item {payload.item_id} not found on this order")
        item.picked = True
        if order.status not in ("PICKING",):
            order.status = "PICKING"

    elif payload.action == "report_damaged":
        if payload.item_id is None:
            raise HTTPException(status_code=400, detail="item_id is required for report_damaged")
        item = next((i for i in order.items if i.id == payload.item_id), None)
        if not item:
            raise HTTPException(status_code=404, detail=f"Order item {payload.item_id} not found on this order")
        item.damaged_reported = True
        item.damage_note = payload.note

    elif payload.action == "complete":
        order.status = "PICKED"
        order.picking_completed_at = datetime.datetime.utcnow()

    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {payload.action}")

    db.commit()
    db.refresh(order)
    return serializers.order_to_detail(order, services.latest_risk_out(order))
