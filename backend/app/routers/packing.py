import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas, services
from ..database import get_db

router = APIRouter(prefix="/api/orders", tags=["packing"])


def _load(db: Session, order_id: int) -> models.Order:
    order = (
        db.query(models.Order)
        .options(joinedload(models.Order.items).joinedload(models.OrderItem.product), joinedload(models.Order.packing_plan))
        .filter(models.Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return order


def _plan_out(plan: models.PackingPlan) -> dict:
    return {
        "order_id": plan.order_id,
        "status": plan.status,
        "notes": plan.notes,
        "bags": json.loads(plan.plan_json),
    }


@router.get("/{order_id}/packing-plan")
def get_packing_plan(order_id: int, db: Session = Depends(get_db)):
    order = _load(db, order_id)
    plan = services.get_or_create_packing_plan(db, order)
    return _plan_out(plan)


@router.post("/{order_id}/packing")
def packing_action(order_id: int, payload: schemas.PackingAction, db: Session = Depends(get_db)):
    order = _load(db, order_id)
    plan = services.get_or_create_packing_plan(db, order)

    if payload.action == "confirm":
        plan.status = "confirmed"
        order.status = "PACKED"
        import datetime

        order.packing_confirmed_at = datetime.datetime.utcnow()

    elif payload.action == "modify":
        if not payload.bags:
            raise HTTPException(status_code=400, detail="bags is required for modify")
        plan.plan_json = json.dumps([b.model_dump() for b in payload.bags])
        plan.status = "modified"
        order.status = "PACKED"
        import datetime

        order.packing_confirmed_at = datetime.datetime.utcnow()

    elif payload.action == "report_issue":
        plan.status = "issue_reported"
        plan.notes = payload.note

    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {payload.action}")

    db.commit()
    db.refresh(plan)
    return _plan_out(plan)
