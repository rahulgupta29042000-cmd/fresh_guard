import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    customer_name: str
    warehouse_id: int
    distance_km: float = Field(gt=0)
    items: List[OrderItemCreate]
    picker_id: Optional[int] = None
    rider_id: Optional[int] = None


class ProductOut(BaseModel):
    id: int
    name: str
    category: str
    emoji: str
    weight_kg: float
    fragility_score: float
    temperature_sensitive: bool
    packaging_type: str
    historical_damage_rate: float

    model_config = ConfigDict(from_attributes=True)


class OrderItemOut(BaseModel):
    id: int
    product: ProductOut
    quantity: int
    picked: bool
    damaged_reported: bool
    damage_note: Optional[str] = None
    product_risk: Optional[float] = None
    requires_inspection: str = "none"  # none | recommended | required
    quality_check_status: Optional[str] = None  # PENDING | PASSED | FAILED
    replaced: bool = False
    replaced_by_item_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class RiskFactor(BaseModel):
    factor: str
    impact: str  # low | medium | high


class RiskComponentScores(BaseModel):
    product_risk: float
    order_complexity: float
    warehouse_risk: float
    delivery_risk: float
    handling_risk: float


class RiskResult(BaseModel):
    riskScore: int
    riskLevel: str
    modelVersion: str
    predictionSource: str
    componentScores: RiskComponentScores
    riskFactors: List[RiskFactor]
    recommendations: List[str]


class OrderOut(BaseModel):
    id: int
    order_code: str
    customer_name: str
    warehouse_id: int
    warehouse_name: str
    picker_id: Optional[int]
    rider_id: Optional[int]
    order_time: datetime.datetime
    total_weight: float
    distance_km: float
    status: str
    risk_score: Optional[int]
    risk_level: Optional[str]
    item_count: int

    model_config = ConfigDict(from_attributes=True)


class OrderDetailOut(OrderOut):
    items: List[OrderItemOut]
    risk: Optional[RiskResult] = None


class RecommendationOut(BaseModel):
    id: int
    type: str
    instruction: str
    priority: str
    completed: bool

    model_config = ConfigDict(from_attributes=True)


class PickingAction(BaseModel):
    action: str  # start | mark_item_picked | report_damaged | complete
    item_id: Optional[int] = None
    note: Optional[str] = None


class PackingBagItem(BaseModel):
    order_item_id: int
    name: str


class PackingBag(BaseModel):
    bag_name: str
    category: str
    items: List[PackingBagItem]


class PackingAction(BaseModel):
    action: str  # confirm | modify | report_issue
    bags: Optional[List[PackingBag]] = None
    note: Optional[str] = None


class DeliveryAction(BaseModel):
    action: str  # accept_instructions | mark_delivered


class FeedbackCreate(BaseModel):
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    issue_type: str = "none"
    comments: Optional[str] = None


class DashboardKpis(BaseModel):
    damage_free_rate: float
    damage_free_rate_change: float
    orders_today: int
    high_risk_orders_today: int
    damage_rate: float
    refund_rate: float


class DashboardAnalytics(BaseModel):
    kpis: DashboardKpis
    risk_distribution: dict
    top_damaged_categories: List[dict]
    top_problematic_skus: List[dict]
    warehouse_comparison: List[dict]


# ---------------------------------------------------------------------------
# Phase 2 — AI Computer Vision Quality Inspection
# ---------------------------------------------------------------------------


class ImageUploadSampleRequest(BaseModel):
    sample_key: str


class InspectionCreate(BaseModel):
    order_id: int
    order_item_id: int
    image_id: Optional[int] = None


class InspectionHumanDecision(BaseModel):
    note: Optional[str] = None


class ReplaceRequest(BaseModel):
    replacement_product_id: int
    reason: Optional[str] = None
