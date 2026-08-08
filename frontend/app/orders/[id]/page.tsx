"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, OrderDetail } from "@/lib/api";
import RiskBadge from "@/components/RiskBadge";
import RiskGauge from "@/components/RiskGauge";
import { LoadingState, ErrorState } from "@/components/States";

const COMPONENT_LABELS: Record<string, string> = {
  product_risk: "Product Risk",
  order_complexity: "Order Complexity",
  warehouse_risk: "Warehouse Risk",
  delivery_risk: "Delivery Risk",
  handling_risk: "Handling Risk",
};

const IMPACT_STYLES: Record<string, string> = {
  high: "text-red-400",
  medium: "text-amber-400",
  low: "text-[#8b93ab]",
};

const NEXT_STEP: Record<string, { href: (id: number) => string; label: string }> = {
  CREATED: { href: () => "/picker", label: "Go to Picker Workflow" },
  RISK_ASSESSED: { href: () => "/picker", label: "Go to Picker Workflow" },
  PICKING: { href: () => "/picker", label: "Continue Picking" },
  PICKED: { href: (id) => `/packing/${id}`, label: "Go to Packing" },
  PACKING: { href: (id) => `/packing/${id}`, label: "Go to Packing" },
  PACKED: { href: (id) => `/delivery/${id}`, label: "Go to Delivery" },
  DISPATCHED: { href: (id) => `/delivery/${id}`, label: "View Delivery" },
  DELIVERED: { href: (id) => `/feedback/${id}`, label: "Go to Feedback" },
};

export default function OrderDetailPage() {
  const params = useParams();
  const id = Number(params.id);
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [recalculating, setRecalculating] = useState(false);

  function load() {
    api
      .getOrder(id)
      .then(setOrder)
      .catch((e) => setError(String(e)));
  }

  useEffect(load, [id]);

  async function recalc() {
    setRecalculating(true);
    try {
      await api.recalculateRisk(id);
      load();
    } catch (e) {
      setError(String(e));
    } finally {
      setRecalculating(false);
    }
  }

  if (error) return <ErrorState message={error} />;
  if (!order) return <LoadingState label="Loading order..." />;

  const next = NEXT_STEP[order.status];

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">{order.order_code}</h1>
            <RiskBadge level={order.risk_level} />
          </div>
          <p className="text-sm text-[#8b93ab] mt-1">
            {order.customer_name} · {order.warehouse_name} · {new Date(order.order_time).toLocaleString()}
          </p>
        </div>
        <div className="flex gap-2">
          <button className="btn btn-secondary" onClick={recalc} disabled={recalculating}>
            {recalculating ? "Recalculating..." : "Recalculate Risk"}
          </button>
          {next && (
            <Link href={next.href(order.id)} className="btn btn-primary">
              {next.label}
            </Link>
          )}
        </div>
      </div>

      {!order.risk ? (
        <ErrorState message="AI risk assessment unavailable for this order. Continue with standard fulfillment workflow." />
      ) : (
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="card p-6 flex flex-col items-center justify-center">
            <RiskGauge score={order.risk.riskScore} level={order.risk.riskLevel} />
            <p className="text-xs text-[#8b93ab] mt-4 text-center">
              Model: {order.risk.modelVersion} ({order.risk.predictionSource === "ml_model" ? "AI prediction" : "rule-based fallback"})
            </p>
            <p className="text-xs text-[#5b6480] mt-1 text-center">Prototype model — synthetic data, not a certainty.</p>
          </div>

          <div className="card p-6 lg:col-span-2">
            <h2 className="font-semibold mb-4">Risk Breakdown</h2>
            <div className="space-y-3">
              {Object.entries(order.risk.componentScores).map(([key, value]) => (
                <div key={key} className="flex items-center gap-3">
                  <span className="w-36 text-sm text-[#c3c9dc]">{COMPONENT_LABELS[key] || key}</span>
                  <div className="flex-1 h-2.5 rounded-full bg-[#1b2233] overflow-hidden">
                    <div className="h-full rounded-full bg-[#4f7cff]" style={{ width: `${value}%` }} />
                  </div>
                  <span className="w-10 text-right text-sm font-medium">{Math.round(value)}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="card p-6">
            <h2 className="font-semibold mb-4">Top Risk Factors</h2>
            <ul className="space-y-2">
              {order.risk.riskFactors.map((f, i) => (
                <li key={i} className="text-sm flex items-start gap-2">
                  <span className={`font-semibold ${IMPACT_STYLES[f.impact]}`}>●</span>
                  <span>{f.factor}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="card p-6 lg:col-span-2">
            <h2 className="font-semibold mb-4">Recommended Actions</h2>
            <ul className="space-y-2">
              {order.risk.recommendations.map((r, i) => (
                <li key={i} className="text-sm flex items-start gap-2">
                  <span className="text-emerald-400">✓</span>
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      <div className="card p-6">
        <h2 className="font-semibold mb-4">Order Items</h2>
        <table className="data-table">
          <thead>
            <tr>
              <th>Product</th>
              <th>Qty</th>
              <th>Fragility</th>
              <th>Temp-Sensitive</th>
              <th>Product Risk</th>
              <th>Status</th>
              <th>AI Inspection</th>
            </tr>
          </thead>
          <tbody>
            {order.items.map((item) => (
              <tr key={item.id} className={item.replaced ? "opacity-40" : ""}>
                <td>
                  {item.product.emoji} {item.product.name}
                  {item.replaced && <span className="text-xs text-[#8b93ab]"> (replaced)</span>}
                </td>
                <td>{item.quantity}</td>
                <td>{item.product.fragility_score}</td>
                <td>{item.product.temperature_sensitive ? "Yes" : "No"}</td>
                <td>{item.product_risk}</td>
                <td>
                  {item.damaged_reported ? (
                    <span className="text-red-400">Damaged reported</span>
                  ) : item.picked ? (
                    <span className="text-emerald-400">Picked</span>
                  ) : (
                    <span className="text-[#8b93ab]">Pending</span>
                  )}
                </td>
                <td>
                  {item.requires_inspection === "none" ? (
                    <span className="text-[#5b6480]">—</span>
                  ) : item.quality_check_status === "PASSED" ? (
                    <span className="text-emerald-400">✓ PASS</span>
                  ) : item.quality_check_status === "FAILED" ? (
                    <span className="text-red-400">✗ Replaced</span>
                  ) : (
                    <Link href={`/inspection/${order.id}/${item.id}`} className="text-[#4f7cff] hover:underline">
                      {item.requires_inspection === "required" ? "Required →" : "Optional →"}
                    </Link>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
