const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type RiskFactor = { factor: string; impact: "low" | "medium" | "high" };

export type RiskComponentScores = {
  product_risk: number;
  order_complexity: number;
  warehouse_risk: number;
  delivery_risk: number;
  handling_risk: number;
};

export type RiskResult = {
  riskScore: number;
  riskLevel: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  modelVersion: string;
  predictionSource: "ml_model" | "rule_based_fallback";
  componentScores: RiskComponentScores;
  riskFactors: RiskFactor[];
  recommendations: string[];
};

export type Product = {
  id: number;
  name: string;
  category: string;
  emoji: string;
  weight_kg: number;
  fragility_score: number;
  temperature_sensitive: boolean;
  packaging_type: string;
  historical_damage_rate: number;
};

export type OrderItem = {
  id: number;
  product: Product;
  quantity: number;
  picked: boolean;
  damaged_reported: boolean;
  damage_note: string | null;
  product_risk: number;
  requires_inspection: "none" | "recommended" | "required";
  quality_check_status: "PENDING" | "PASSED" | "FAILED" | null;
  replaced: boolean;
  replaced_by_item_id: number | null;
};

export type Order = {
  id: number;
  order_code: string;
  customer_name: string;
  warehouse_id: number;
  warehouse_name: string;
  picker_id: number | null;
  rider_id: number | null;
  order_time: string;
  total_weight: number;
  distance_km: number;
  status: string;
  risk_score: number | null;
  risk_level: string | null;
  item_count: number;
};

export type OrderDetail = Order & {
  items: OrderItem[];
  risk: RiskResult | null;
};

export type Recommendation = {
  id: number;
  type: string;
  instruction: string;
  priority: string;
  completed: boolean;
};

export type Warehouse = {
  id: number;
  name: string;
  location: string;
  capacity: number;
  current_load: number;
  load_ratio: number;
};

export type DashboardData = {
  kpis: {
    damage_free_rate: number;
    damage_free_rate_change: number;
    orders_today: number;
    high_risk_orders_today: number;
    damage_rate: number;
    refund_rate: number;
  };
  risk_distribution: Record<string, number>;
  top_damaged_categories: { category: string; count: number }[];
  top_problematic_skus: { product: string; count: number }[];
  warehouse_comparison: { warehouse: string; orders: number; damage_free_rate: number; current_load: number; capacity: number }[];
  ai_inspection: InspectionKpis;
};

// ---------------------------------------------------------------------------
// Phase 2 — AI Computer Vision Quality Inspection
// ---------------------------------------------------------------------------

export type InspectionKpis = {
  inspected: number;
  passed: number;
  review: number;
  rejected: number;
  rejectRate: number;
  humanReviewedCount: number;
  humanOverrideRate: number;
};

export type SampleImage = { key: string; label: string; product_hint: string; file: string };

export type ImageOut = {
  id: number;
  url: string;
  imageQuality: { score: number; status: "good" | "poor"; issues: string[] };
  createdAt: string;
};

export type Defect = { type: string; confidence: number; severity: "low" | "medium" | "high"; description: string | null };

export type Inspection = {
  inspectionId: number;
  orderId: number;
  orderCode: string;
  orderItemId: number;
  product: { id: number; name: string; emoji: string; category: string };
  attemptNumber: number;
  qualityScore: number | null;
  inspectionStatus: "PENDING" | "PASS" | "REVIEW" | "REJECT";
  aiDecision: "PASS" | "REVIEW" | "REJECT" | null;
  humanDecision: "ACCEPT" | "REJECT" | null;
  mandatoryHumanReview: boolean;
  modelVersion: string | null;
  visionMode: string;
  inspectionTimeMs: number | null;
  image: ImageOut | null;
  defects: Defect[];
  reviewedAt: string | null;
  reviewedBy: string | null;
  createdAt: string;
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  listOrders: (params: Record<string, string> = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request<Order[]>(`/api/orders${qs ? `?${qs}` : ""}`);
  },
  getOrder: (id: number) => request<OrderDetail>(`/api/orders/${id}`),
  createOrder: (payload: {
    customer_name: string;
    warehouse_id: number;
    distance_km: number;
    items: { product_id: number; quantity: number }[];
  }) => request<OrderDetail>("/api/orders", { method: "POST", body: JSON.stringify(payload) }),
  recalculateRisk: (id: number) => request<RiskResult>(`/api/orders/${id}/recalculate-risk`, { method: "POST" }),
  getRecommendations: (id: number) => request<Recommendation[]>(`/api/orders/${id}/recommendations`),

  pickingAction: (id: number, action: string, item_id?: number, note?: string) =>
    request<OrderDetail>(`/api/orders/${id}/picking`, { method: "POST", body: JSON.stringify({ action, item_id, note }) }),

  getPackingPlan: (id: number) => request<any>(`/api/orders/${id}/packing-plan`),
  packingAction: (id: number, action: string, bags?: any, note?: string) =>
    request<any>(`/api/orders/${id}/packing`, { method: "POST", body: JSON.stringify({ action, bags, note }) }),

  getDeliveryInstructions: (id: number) => request<any>(`/api/orders/${id}/delivery`),
  deliveryAction: (id: number, action: string) =>
    request<any>(`/api/orders/${id}/delivery`, { method: "POST", body: JSON.stringify({ action }) }),

  submitFeedback: (id: number, payload: { rating?: number; issue_type: string; comments?: string }) =>
    request<any>(`/api/orders/${id}/feedback`, { method: "POST", body: JSON.stringify(payload) }),
  getFeedback: (id: number) => request<any | null>(`/api/orders/${id}/feedback`),

  listProducts: () => request<Product[]>("/api/products"),
  listWarehouses: () => request<Warehouse[]>("/api/warehouses"),
  listUsers: (role?: string) => request<any[]>(`/api/users${role ? `?role=${role}` : ""}`),

  getDashboard: () => request<DashboardData>("/api/dashboard"),

  // Phase 2 — inspection
  listSampleImages: () => request<SampleImage[]>("/api/images/samples"),
  uploadSampleImage: (sample_key: string) =>
    request<ImageOut>("/api/images/upload-sample", { method: "POST", body: JSON.stringify({ sample_key }) }),
  uploadImageFile: async (file: File): Promise<ImageOut> => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/api/images/upload`, { method: "POST", body: formData });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
    return res.json();
  },

  createInspection: (order_id: number, order_item_id: number, image_id?: number) =>
    request<Inspection>("/api/inspections", { method: "POST", body: JSON.stringify({ order_id, order_item_id, image_id }) }),
  attachImage: (inspectionId: number, image_id: number) =>
    request<Inspection>(`/api/inspections/${inspectionId}/image`, { method: "POST", body: JSON.stringify({ image_id }) }),
  analyzeInspection: (inspectionId: number) =>
    request<Inspection>(`/api/inspections/${inspectionId}/analyze`, { method: "POST" }),
  acceptInspection: (inspectionId: number) =>
    request<Inspection>(`/api/inspections/${inspectionId}/accept`, { method: "POST" }),
  rejectInspection: (inspectionId: number) =>
    request<Inspection>(`/api/inspections/${inspectionId}/reject`, { method: "POST" }),
  reinspect: (inspectionId: number) =>
    request<Inspection>(`/api/inspections/${inspectionId}/reinspect`, { method: "POST" }),
  replaceItem: (inspectionId: number, replacement_product_id: number, reason?: string) =>
    request<{ newOrderItem: OrderItem; newInspectionId: number; escalate: boolean; rejectionCount: number }>(
      `/api/inspections/${inspectionId}/replace`,
      { method: "POST", body: JSON.stringify({ replacement_product_id, reason }) }
    ),
  getInspection: (inspectionId: number) => request<Inspection>(`/api/inspections/${inspectionId}`),
  listInspections: (params: Record<string, string> = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request<Inspection[]>(`/api/inspections${qs ? `?${qs}` : ""}`);
  },

  getReviewQueue: () => request<{ count: number; items: Inspection[] }>("/api/qc/review-queue"),

  getInspectionAnalytics: () => request<any>("/api/analytics/inspections"),
  getDefectAnalytics: () => request<any>("/api/analytics/defects"),
};
