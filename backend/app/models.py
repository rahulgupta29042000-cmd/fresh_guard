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
    inspections = relationship("Inspection", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    picked = Column(Boolean, default=False)
    damaged_reported = Column(Boolean, default=False)
    damage_note = Column(Text, nullable=True)

    # Phase 2 — AI visual quality inspection
    requires_inspection = Column(String, default="none")  # none | recommended | required
    quality_check_status = Column(String, nullable=True)  # PENDING | PASSED | FAILED
    replaced = Column(Boolean, default=False)  # true once superseded by a replacement item
    replaced_by_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=True)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
    inspections = relationship(
        "Inspection", back_populates="order_item", cascade="all, delete-orphan",
        foreign_keys="Inspection.order_item_id",
    )


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
    flagged_as_possible_ai_miss = Column(Boolean, default=False)  # set when a PASSed item gets a damage complaint

    order = relationship("Order", back_populates="feedback")


# ---------------------------------------------------------------------------
# Phase 2 — AI Computer Vision Quality Inspection
# ---------------------------------------------------------------------------


class InspectionImage(Base):
    __tablename__ = "inspection_images"

    id = Column(Integer, primary_key=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=True)
    file_path = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    image_quality_score = Column(Float, nullable=True)  # 0-100
    image_quality_status = Column(String, nullable=True)  # good | poor
    image_quality_issues = Column(Text, nullable=True)  # JSON list of strings
    created_at = Column(DateTime, default=now)

    inspection = relationship("Inspection", back_populates="image", foreign_keys=[inspection_id])


class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    attempt_number = Column(Integer, default=1)  # 1st scan, 2nd (replacement) scan, ...
    quality_score = Column(Float, nullable=True)  # 0-100
    inspection_status = Column(String, default="PENDING")  # PENDING | PASS | REVIEW | REJECT
    ai_decision = Column(String, nullable=True)  # PASS | REVIEW | REJECT (raw AI output, never overwritten)
    human_decision = Column(String, nullable=True)  # ACCEPT | REJECT
    mandatory_human_review = Column(Boolean, default=False)  # CRITICAL-risk orders review even AI PASS
    model_version = Column(String, nullable=True)
    vision_mode = Column(String, default="simulation")  # simulation | (future real provider name)
    inspection_time_ms = Column(Integer, nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now)

    order = relationship("Order", back_populates="inspections")
    order_item = relationship("OrderItem", back_populates="inspections", foreign_keys=[order_item_id])
    product = relationship("Product")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    # One-way FK (inspection_images.inspection_id -> inspections.id) — a
    # standalone-uploaded image gets attached by updating its inspection_id.
    image = relationship("InspectionImage", back_populates="inspection", uselist=False, foreign_keys=[InspectionImage.inspection_id])
    defects = relationship("InspectionDefect", back_populates="inspection", cascade="all, delete-orphan")
    model_prediction = relationship(
        "ModelPrediction", back_populates="inspection", uselist=False, cascade="all, delete-orphan"
    )


class InspectionDefect(Base):
    __tablename__ = "inspection_defects"

    id = Column(Integer, primary_key=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=False)
    defect_type = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)  # 0-1
    severity = Column(String, nullable=False)  # low | medium | high
    description = Column(String, nullable=True)

    inspection = relationship("Inspection", back_populates="defects")


class ReplacementEvent(Base):
    __tablename__ = "replacement_events"

    id = Column(Integer, primary_key=True)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=False)  # the new (replacement) item
    original_product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    replacement_product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    reason = Column(String, nullable=False)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=False)  # the rejected inspection
    created_at = Column(DateTime, default=now)


class ModelPrediction(Base):
    """Raw AI output, kept separate from the business Inspection record for
    model-evaluation-dataset purposes (ground truth vs. prediction vs. human decision)."""

    __tablename__ = "model_predictions"

    id = Column(Integer, primary_key=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), unique=True, nullable=False)
    model_version = Column(String, nullable=False)
    prediction = Column(String, nullable=False)  # PASS | REVIEW | REJECT
    confidence = Column(Float, nullable=True)  # overall/max defect confidence, 0-1
    raw_result = Column(Text, nullable=False)  # JSON — full structured vision output
    created_at = Column(DateTime, default=now)

    inspection = relationship("Inspection", back_populates="model_prediction")
