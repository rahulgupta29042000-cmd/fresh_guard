"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Order } from "@/lib/api";
import RiskBadge from "@/components/RiskBadge";
import { LoadingState, ErrorState, EmptyState } from "@/components/States";

const RISK_LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];
const STATUSES = [
  "CREATED",
  "RISK_ASSESSED",
  "PICKING",
  "PICKED",
  "PACKING",
  "PACKED",
  "DISPATCHED",
  "DELIVERED",
  "FEEDBACK_RECEIVED",
];

const INSPECTION_STATUS_STYLE: Record<string, { label: string; className: string }> = {
  not_required: { label: "Not Required", className: "text-[#5b6480]" },
  pending: { label: "Pending", className: "text-amber-400" },
  passed: { label: "Passed", className: "text-emerald-400" },
  issues: { label: "Issues", className: "text-red-400" },
};

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [riskLevel, setRiskLevel] = useState("");
  const [status, setStatus] = useState("");
  const [date, setDate] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    const t = setTimeout(() => setSearch(searchInput.trim()), 350);
    return () => clearTimeout(t);
  }, [searchInput]);

  function load() {
    const params: Record<string, string> = {};
    if (riskLevel) params.risk_level = riskLevel;
    if (status) params.status = status;
    if (date) params.date = date;
    if (search) params.search = search;
    api
      .listOrders(params)
      .then(setOrders)
      .catch((e) => setError(String(e)));
  }

  useEffect(load, [riskLevel, status, date, search]);

  const hasFilters = riskLevel || status || date || searchInput;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Orders</h1>
      </div>

      <div className="flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Search order ID or product…"
          className="bg-[#161c2c] border border-[#232b40] rounded-lg px-3 py-2 text-sm w-64"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
        />
        <select className="bg-[#161c2c] border border-[#232b40] rounded-lg px-3 py-2 text-sm" value={riskLevel} onChange={(e) => setRiskLevel(e.target.value)}>
          <option value="">All risk levels</option>
          {RISK_LEVELS.map((l) => (
            <option key={l} value={l}>
              {l}
            </option>
          ))}
        </select>
        <select className="bg-[#161c2c] border border-[#232b40] rounded-lg px-3 py-2 text-sm" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s.replace("_", " ")}
            </option>
          ))}
        </select>
        <input
          type="date"
          className="bg-[#161c2c] border border-[#232b40] rounded-lg px-3 py-2 text-sm"
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />
        {hasFilters && (
          <button
            className="text-sm text-[#8b93ab] hover:text-white"
            onClick={() => {
              setRiskLevel("");
              setStatus("");
              setDate("");
              setSearchInput("");
            }}
          >
            Clear filters
          </button>
        )}
      </div>

      {error && <ErrorState message={error} />}
      {!error && !orders && <LoadingState label="Loading orders..." />}
      {!error && orders && orders.length === 0 && <EmptyState message="No orders match these filters." />}

      {!error && orders && orders.length > 0 && (
        <div className="card overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Order ID</th>
                <th>Time</th>
                <th>Items</th>
                <th>Warehouse</th>
                <th>Risk Score</th>
                <th>Risk Level</th>
                <th>Status</th>
                <th>Inspection</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => {
                const insp = INSPECTION_STATUS_STYLE[o.inspection_status] || INSPECTION_STATUS_STYLE.not_required;
                return (
                  <tr key={o.id}>
                    <td className="font-medium">{o.order_code}</td>
                    <td className="text-[#8b93ab]">{new Date(o.order_time).toLocaleString()}</td>
                    <td>{o.item_count}</td>
                    <td>{o.warehouse_name}</td>
                    <td>{o.risk_score ?? "—"}</td>
                    <td>
                      <RiskBadge level={o.risk_level} />
                    </td>
                    <td className="text-[#8b93ab]">{o.status.replace("_", " ")}</td>
                    <td className={insp.className}>{insp.label}</td>
                    <td>
                      <Link href={`/orders/${o.id}`} className="text-[#4f7cff] hover:underline text-sm">
                        View →
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
