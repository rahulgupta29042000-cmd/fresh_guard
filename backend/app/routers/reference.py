from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db

router = APIRouter(prefix="/api", tags=["reference"])


@router.get("/products")
def list_products(db: Session = Depends(get_db)):
    products = db.query(models.Product).order_by(models.Product.name).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "emoji": p.emoji,
            "weight_kg": p.weight_kg,
            "fragility_score": p.fragility_score,
            "temperature_sensitive": p.temperature_sensitive,
            "packaging_type": p.packaging_type,
            "historical_damage_rate": p.historical_damage_rate,
        }
        for p in products
    ]


@router.get("/warehouses")
def list_warehouses(db: Session = Depends(get_db)):
    warehouses = db.query(models.Warehouse).order_by(models.Warehouse.name).all()
    return [
        {
            "id": w.id,
            "name": w.name,
            "location": w.location,
            "capacity": w.capacity,
            "current_load": w.current_load,
            "load_ratio": round(w.current_load / w.capacity, 2) if w.capacity else 0,
        }
        for w in warehouses
    ]


@router.get("/users")
def list_users(role: Optional[str] = Query(default=None), warehouse_id: Optional[int] = Query(default=None), db: Session = Depends(get_db)):
    q = db.query(models.User)
    if role:
        q = q.filter(models.User.role == role)
    if warehouse_id:
        q = q.filter(models.User.warehouse_id == warehouse_id)
    users = q.order_by(models.User.name).all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "role": u.role,
            "warehouse_id": u.warehouse_id,
            "experience_years": u.experience_years,
            "avg_quality_score": u.avg_quality_score,
            "avg_picking_speed": u.avg_picking_speed,
            "avg_rating": u.avg_rating,
        }
        for u in users
    ]
