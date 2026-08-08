"use client";

import { useEffect, useState } from "react";
import { api, DashboardData } from "@/lib/api";
import StatCard from "@/components/StatCard";
import { LoadingState, ErrorState } from "@/components/States";

const RISK_COLORS: Record<string, string> = {
  LOW: "bg-emerald-400",
  MEDIUM: "bg-amber-400",
  HIGH: "bg-orange-400",
  CRITICAL: "bg-red-400",
};

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getDashboard()
      .then(setData)
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState label="Loading operations dashboard..." />;

  const maxRisk = Math.max(1, ...Object.values(data.risk_distribution));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Operations Dashboard</h1>
        <p className="text-sm text-[#8b93ab] mt-1">
          Fresh_Guard Phase 1 prototype — figures below are computed from seeded synthetic data.
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <StatCard
          label="Damage-Free Orders"
          value={`${data.kpis.damage_free_rate}%`}
          change={`${data.kpis.damage_free_rate_change >= 0 ? "↑" : "↓"} ${Math.abs(data.kpis.damage_free_rate_change)}% vs previous period`}
          changeGood={data.kpis.damage_free_rate_change >= 0}
        />
        <StatCard label="Orders Today" value={String(data.kpis.orders_today)} />
        <StatCard
          label="High-Risk Orders Today"
          value={String(data.kpis.high_risk_orders_today)}
          subtitle="HIGH + CRITICAL"
        />
        <StatCard label="Damage Rate" value={`${data.kpis.damage_rate}%`} />
        <StatCard label="Refund / Replacement Rate" value={`${data.kpis.refund_rate}%`} subtitle="simulated" />
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="card p-5">
          <h2 className="font-semibold mb-4">Risk Prediction Distribution</h2>
          <div className="space-y-3">
            {Object.entries(data.risk_distribution).map(([level, count]) => (
              <div key={level} className="flex items-center gap-3">
                <span className="w-20 text-xs font-medium text-[#8b93ab]">{level}</span>
                <div className="flex-1 h-3 rounded-full bg-[#1b2233] overflow-hidden">
                  <div
                    className={`h-full rounded-full ${RISK_COLORS[level]}`}
                    style={{ width: `${(count / maxRisk) * 100}%` }}
                  />
                </div>
                <span className="w-10 text-right text-sm font-medium">{count}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card p-5">
          <h2 className="font-semibold mb-4">Warehouse Comparison</h2>
          <table className="data-table">
            <thead>
              <tr>
                <th>Warehouse</th>
                <th>Orders</th>
                <th>Damage-Free</th>
                <th>Load</th>
              </tr>
            </thead>
            <tbody>
              {data.warehouse_comparison.map((w) => (
                <tr key={w.warehouse}>
                  <td>{w.warehouse}</td>
                  <td>{w.orders}</td>
                  <td>{w.damage_free_rate}%</td>
                  <td>
                    {w.current_load}/{w.capacity}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card p-5">
          <h2 className="font-semibold mb-4">Top Damaged Categories</h2>
          {data.top_damaged_categories.length === 0 ? (
            <p className="text-sm text-[#8b93ab]">No damage reports yet.</p>
          ) : (
            <ul className="space-y-2">
              {data.top_damaged_categories.map((c) => (
                <li key={c.category} className="flex justify-between text-sm">
                  <span className="capitalize">{c.category}</span>
                  <span className="text-[#8b93ab]">{c.count} reports</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="card p-5">
          <h2 className="font-semibold mb-4">Top Problematic SKUs</h2>
          {data.top_problematic_skus.length === 0 ? (
            <p className="text-sm text-[#8b93ab]">No damage reports yet.</p>
          ) : (
            <ul className="space-y-2">
              {data.top_problematic_skus.map((s) => (
                <li key={s.product} className="flex justify-between text-sm">
                  <span>{s.product}</span>
                  <span className="text-[#8b93ab]">{s.count} reports</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
