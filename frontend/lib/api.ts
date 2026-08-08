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
};
