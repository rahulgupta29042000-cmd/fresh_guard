import datetime
from typing import Optional

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas, serializers, services
from ..database import get_db

router = APIRouter(prefix="/api/orders", tags=["orders"])


def _order_query(db: Session):
    return db.query(models.Order).options(
        joinedload(models.Order.items).joinedload(models.OrderItem.product),
        joinedload(models.Order.customer),
        joinedload(models.Order.warehouse),
        joinedload(models.Order.picker),
        joinedload(models.Order.rider),
        joinedload(models.Order.recommendations),
        joinedload(models.Order.risk_predictions),
    )


@router.post("", response_model=schemas.OrderDetailOut)
def create_order(payload: schemas.OrderCreate, db: Session = Depends(get_db)):
    warehouse = db.get(models.Warehouse, payload.warehouse_id)
    if not warehouse:
        raise HTTPException(status_code=400, detail=f"Warehouse {payload.warehouse_id} not found")
    if not payload.items:
        raise HTTPException(status_code=400, detail="Order must contain at least one item")

    product_ids = [item.product_id for item in payload.items]
    products = {p.id: p for p in db.query(models.Product).filter(models.Product.id.in_(product_ids)).all()}
    missing = set(product_ids) - set(products.keys())
    if missing:
        raise HTTPException(status_code=400, detail=f"Unknown product id(s): {sorted(missing)}")

    if payload.picker_id and not db.get(models.User, payload.picker_id):
        raise HTTPException(status_code=400, detail=f"Picker {payload.picker_id} not found")
    if payload.rider_id and not db.get(models.User, payload.rider_id):
        raise HTTPException(status_code=400, detail=f"Rider {payload.rider_id} not found")

    customer = models.Customer(name=payload.customer_name)
    db.add(customer)
    db.flush()

    order = models.Order(
        order_code="PENDING",
        customer_id=customer.id,
        warehouse_id=payload.warehouse_id,
        picker_id=payload.picker_id,
        rider_id=payload.rider_id,
        order_time=datetime.datetime.utcnow(),
        distance_km=payload.distance_km,
        status="CREATED",
    )
    db.add(order)
    db.flush()
    order.order_code = f"FG-{10000 + order.id}"

    for item in payload.items:
        db.add(models.OrderItem(order_id=order.id, product_id=item.product_id, quantity=item.quantity))
    db.flush()
    db.refresh(order)

    order.total_weight = services.compute_total_weight(order)
    db.commit()
    db.refresh(order)

    risk_out = services.run_risk_assessment(db, order)
    db.refresh(order)

    return serializers.order_to_detail(order, risk_out)


@router.get("", response_model=list[schemas.OrderOut])
def list_orders(
    risk_level: Optional[str] = Query(default=None),
    warehouse_id: Optional[int] = Query(default=None),
    status: Optional[str] = Query(default=None),
    date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    search: Optional[str] = Query(default=None, description="Order code or product name"),
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
):
    q = _order_query(db)
    if risk_level:
        q = q.filter(models.Order.risk_level == risk_level.upper())
    if warehouse_id:
        q = q.filter(models.Order.warehouse_id == warehouse_id)
    if status:
        q = q.filter(models.Order.status == status.upper())
    if date:
        try:
            day = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
        q = q.filter(
            models.Order.order_time >= datetime.datetime.combine(day, datetime.time.min),
            models.Order.order_time <= datetime.datetime.combine(day, datetime.time.max),
        )
    if search:
        pattern = f"%{search.strip()}%"
        matching_order_ids = (
            db.query(models.OrderItem.order_id)
            .join(models.Product, models.OrderItem.product_id == models.Product.id)
            .filter(models.Product.name.ilike(pattern))
        )
        q = q.filter(sa.or_(models.Order.order_code.ilike(pattern), models.Order.id.in_(matching_order_ids)))

    orders = q.order_by(models.Order.order_time.desc()).limit(limit).all()
    return [serializers.order_to_out(o) for o in orders]


@router.get("/{order_id}", response_model=schemas.OrderDetailOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = _order_query(db).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return serializers.order_to_detail(order, services.latest_risk_out(order))


@router.get("/{order_id}/risk", response_model=Optional[schemas.RiskResult])
def get_order_risk(order_id: int, db: Session = Depends(get_db)):
    order = _order_query(db).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    risk = services.latest_risk_out(order)
    if risk is None:
        return None
    return risk


@router.post("/{order_id}/recalculate-risk", response_model=schemas.RiskResult)
def recalculate_risk(order_id: int, db: Session = Depends(get_db)):
    order = _order_query(db).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    risk_out = services.run_risk_assessment(db, order)
    if risk_out is None:
        raise HTTPException(status_code=503, detail="AI risk assessment unavailable. Continue with standard fulfillment workflow.")
    return risk_out


@router.get("/{order_id}/recommendations", response_model=list[schemas.RecommendationOut])
def get_recommendations(order_id: int, db: Session = Depends(get_db)):
    order = services.get_order_or_404(db, order_id)
    return [serializers.recommendation_to_out(r) for r in order.recommendations]
