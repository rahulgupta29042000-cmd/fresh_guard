import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


def now():
    return datetime.datetime.utcnow()


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime, default=now)

    orders = relationship("Order", back_populates="customer")


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    location = Column(String, nullable=False)
    capacity = Column(Integer, default=100)  # orders it can comfortably handle at once
    current_load = Column(Integer, default=0)  # orders currently pending fulfillment
    created_at = Column(DateTime, default=now)

    users = relationship("User", back_populates="warehouse")
    orders = relationship("Order", back_populates="warehouse")


class User(Base):
    """Pickers, riders, and managers. role in: picker, rider, manager, admin."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    experience_years = Column(Float, default=1.0)
    avg_quality_score = Column(Float, default=80.0)  # 0-100, historical handling quality
    avg_picking_speed = Column(Float, default=6.0)  # items/minute
    avg_rating = Column(Float, default=4.5)  # rider delivery rating, 0-5
    created_at = Column(DateTime, default=now)

    warehouse = relationship("Warehouse", back_populates="users")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    emoji = Column(String, default="📦")
    weight_kg = Column(Float, nullable=False)
    fragility_score = Column(Float, nullable=False)  # 0-100
    temperature_sensitive = Column(Boolean, default=False)
    packaging_type = Column(String, default="box")
    historical_damage_rate = Column(Float, default=0.05)  # 0-1

    order_items = relationship("OrderItem", back_populates="product")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    order_code = Column(String, unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    picker_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    rider_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    order_time = Column(DateTime, default=now)
    total_weight = Column(Float, default=0.0)
    distance_km = Column(Float, nullable=False)
    status = Column(String, default="CREATED")

    risk_score = Column(Integer, nullable=True)
    risk_level = Column(String, nullable=True)

    picking_started_at = Column(DateTime, nullable=True)
    picking_completed_at = Column(DateTime, nullable=True)
    packing_confirmed_at = Column(DateTime, nullable=True)
    dispatched_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=now)

    customer = relationship("Customer", back_populates="orders")
    warehouse = relationship("Warehouse", back_populates="orders")
    picker = relationship("User", foreign_keys=[picker_id])
    rider = relationship("User", foreign_keys=[rider_id])
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    risk_predictions = relationship("RiskPrediction", back_populates="order", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="order", cascade="all, delete-orphan")
    packing_plan = relationship("PackingPlan", back_populates="order", uselist=False, cascade="all, delete-orphan")
    delivery_instruction = relationship(
        "DeliveryInstruction", back_populates="order", uselist=False, cascade="all, delete-orphan"
    )
    feedback = relationship("Feedback", back_populates="order", uselist=False, cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    picked = Column(Boolean, default=False)
    damaged_reported = Column(Boolean, default=False)
    damage_note = Column(Text, nullable=True)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class RiskPrediction(Base):
    __tablename__ = "risk_predictions"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    risk_score = Column(Integer, nullable=False)
    risk_level = Column(String, nullable=False)
    risk_factors = Column(Text, nullable=False)  # JSON list of {factor, impact}
    component_scores = Column(Text, nullable=False)  # JSON dict
    model_version = Column(String, nullable=False)
    prediction_source = Column(String, nullable=False)  # ml_model | rule_based_fallback
    created_at = Column(DateTime, default=now)

    order = relationship("Order", back_populates="risk_predictions")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    type = Column(String, nullable=False)
    instruction = Column(Text, nullable=False)
    priority = Column(String, default="medium")  # low | medium | high | critical
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now)

    order = relationship("Order", back_populates="recommendations")


class PackingPlan(Base):
    __tablename__ = "packing_plans"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True, nullable=False)
    plan_json = Column(Text, nullable=False)  # [{bag_name, category, items:[...]}]
    status = Column(String, default="proposed")  # proposed | confirmed | modified | issue_reported
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    order = relationship("Order", back_populates="packing_plan")


class DeliveryInstruction(Base):
    __tablename__ = "delivery_instructions"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True, nullable=False)
    instructions_json = Column(Text, nullable=False)  # JSON list of strings
    fragile_item_count = Column(Integer, default=0)
    temperature_sensitive_item_count = Column(Integer, default=0)
    accepted = Column(Boolean, default=False)
    accepted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now)

    order = relationship("Order", back_populates="delivery_instruction")


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True, nullable=False)
    rating = Column(Integer, nullable=True)  # 1-5
    issue_type = Column(String, default="none")
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now)

    order = relationship("Order", back_populates="feedback")
