"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Order, OrderDetail } from "@/lib/api";
import RiskBadge from "@/components/RiskBadge";
import { LoadingState, ErrorState, EmptyState } from "@/components/States";

export default function PickerPage() {
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  function loadList() {
    Promise.all([
      api.listOrders({ status: "RISK_ASSESSED" }),
      api.listOrders({ status: "PICKING" }),
    ])
      .then(([a, b]) => {
        const combined = [...b, ...a];
        setOrders(combined);
        if (!selectedId && combined.length > 0) setSelectedId(combined[0].id);
      })
      .catch((e) => setError(String(e)));
  }

  function loadOrder(id: number) {
    api
      .getOrder(id)
      .then(setOrder)
      .catch((e) => setError(String(e)));
  }

  useEffect(loadList, []);
  useEffect(() => {
    if (selectedId) loadOrder(selectedId);
  }, [selectedId]);

  async function act(action: string, item_id?: number, note?: string) {
    if (!order) return;
    try {
      await api.pickingAction(order.id, action, item_id, note);
      loadOrder(order.id);
      loadList();
    } catch (e) {
      setError(String(e));
    }
  }

  if (error) return <ErrorState message={error} />;

  return (
    <div className="grid lg:grid-cols-[280px_1fr] gap-6">
      <div className="space-y-3">
        <h1 className="text-xl font-bold">Picker Queue</h1>
        {!orders && <LoadingState label="Loading queue..." />}
        {orders && orders.length === 0 && <EmptyState message="No orders waiting to be picked." />}
        {orders && orders.length > 0 && (
          <div className="space-y-2">
            {orders.map((o) => (
              <button
                key={o.id}
                onClick={() => setSelectedId(o.id)}
                className={`w-full text-left card p-3 transition-colors ${
                  selectedId === o.id ? "border-[#4f7cff]" : ""
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-sm">{o.order_code}</span>
                  <RiskBadge level={o.risk_level} />
                </div>
                <div className="text-xs text-[#8b93ab] mt-1">
                  {o.item_count} items · {o.warehouse_name}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      <div>
        {!order && <LoadingState label="Select an order from the queue." />}
        {order && (
          <div className="card p-6 space-y-5">
            <div className="flex items-start justify-between flex-wrap gap-3">
              <div>
                <div className="flex items-center gap-3">
                  <h2 className="text-xl font-bold">{order.order_code}</h2>
                  <RiskBadge level={order.risk_level} />
                </div>
                {order.risk && (order.risk.riskLevel === "HIGH" || order.risk.riskLevel === "CRITICAL") && (
                  <p className="text-sm text-orange-400 mt-1">⚠️ Special handling required</p>
                )}
              </div>
              <div className="flex gap-2">
                {order.status !== "PICKING" && order.status !== "PICKED" && (
                  <button className="btn btn-primary" onClick={() => act("start")}>
                    Start Picking
                  </button>
                )}
                {order.status === "PICKING" && (
                  <button className="btn btn-primary" onClick={() => act("complete")}>
                    Complete Order
                  </button>
                )}
              </div>
            </div>

            {order.risk && order.risk.recommendations.length > 0 && (
              <div className="bg-[#1a2136] rounded-lg p-4">
                <div className="text-xs uppercase tracking-wide text-[#8b93ab] font-medium mb-2">Handling Guidance</div>
                <ul className="space-y-1 text-sm">
                  {order.risk.recommendations.map((r, i) => (
                    <li key={i}>✓ {r}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="space-y-3">
              {order.items
                .filter((item) => !item.replaced)
                .map((item) => {
                  const specialHandling = item.product.fragility_score >= 65 || item.product.temperature_sensitive;
                  return (
                    <div key={item.id} className="border border-[#232b40] rounded-lg p-4">
                      <div className="flex items-center justify-between flex-wrap gap-2">
                        <div>
                          <div className="font-medium">
                            {item.product.emoji} {item.product.name} <span className="text-[#8b93ab] text-sm">× {item.quantity}</span>
                          </div>
                          <div className="text-xs mt-1">
                            {item.product.fragility_score >= 65 && (
                              <span className="text-red-400 font-semibold">FRAGILE — HANDLE SEPARATELY</span>
                            )}
                            {item.product.temperature_sensitive && (
                              <span className="text-blue-400 font-semibold ml-2">TEMPERATURE-SENSITIVE</span>
                            )}
                            {!specialHandling && item.requires_inspection === "none" && (
                              <span className="text-[#8b93ab]">Normal handling</span>
                            )}
                          </div>
                          {item.quality_check_status && (
                            <div className="text-xs mt-1">
                              {item.quality_check_status === "PASSED" && (
                                <span className="text-emerald-400">✓ Quality check completed — PASS</span>
                              )}
                              {item.quality_check_status === "FAILED" && (
                                <span className="text-red-400">✗ Quality check failed — replaced</span>
                              )}
                              {item.quality_check_status === "PENDING" && (
                                <span className="text-amber-400">Quality check in progress…</span>
                              )}
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          {item.requires_inspection !== "none" && !item.quality_check_status && (
                            <Link
                              href={`/inspection/${order.id}/${item.id}`}
                              className={item.requires_inspection === "required" ? "btn btn-danger text-xs" : "btn btn-secondary text-xs"}
                            >
                              Inspect with AI{item.requires_inspection === "recommended" ? " (optional)" : ""}
                            </Link>
                          )}
                          {item.picked ? (
                            <span className="text-emerald-400 text-sm font-medium">✓ Picked</span>
                          ) : (
                            <button className="btn btn-secondary text-xs" onClick={() => act("mark_item_picked", item.id)}>
                              Mark Item Picked
                            </button>
                          )}
                          {item.damaged_reported ? (
                            <span className="text-red-400 text-sm font-medium">Damage reported</span>
                          ) : (
                            <button
                              className="btn btn-danger text-xs"
                              onClick={() => act("report_damaged", item.id, "Reported at picking")}
                            >
                              Report Damaged Item
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
