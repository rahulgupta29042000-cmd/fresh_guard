"use client";

import { useEffect, useState } from "react";
import { api, AnalyticsOverview } from "@/lib/api";
import StatCard from "@/components/StatCard";
import { LoadingState, ErrorState } from "@/components/States";

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsOverview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getAnalyticsOverview()
      .then(setData)
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState label="Loading analytics..." />;

  const maxTrend = Math.max(1, ...data.qualityTrend.map((t) => t.orders));
  const maxDefect = Math.max(1, ...data.defects.byType.map((d) => d.count));
  const aiTotal = Math.max(1, data.ai.pass + data.ai.review + data.ai.reject);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Quality Analytics</h1>
        <p className="text-sm text-[#8b93ab] mt-1">{data.note}</p>
      </div>

      <div>
        <h2 className="text-lg font-semibold mb-3">Quality</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Damage-Free Rate" value={`${data.quality.damageFreeRate}%`} />
          <StatCard label="Customer Issue Rate" value={`${data.quality.customerIssueRate}%`} />
          <StatCard label="Rejected Products" value={String(data.quality.rejectedProducts)} />
          <StatCard label="AI Inspection Volume" value={String(data.quality.aiInspectionVolume)} />
        </div>
      </div>

      <div>
        <h2 className="text-lg font-semibold mb-3">AI Decisions</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <StatCard label="AI Pass" value={String(data.ai.pass)} />
          <StatCard label="AI Review" value={String(data.ai.review)} />
          <StatCard label="AI Reject" value={String(data.ai.reject)} />
          <StatCard label="Human Overrides" value={String(data.ai.humanOverrides)} subtitle={`${data.ai.humanOverrideRate}% override rate`} />
        </div>
        <div className="card p-5">
          <div className="flex h-4 rounded-full overflow-hidden">
            <div className="bg-emerald-400" style={{ width: `${(data.ai.pass / aiTotal) * 100}%` }} title="Pass" />
            <div className="bg-amber-400" style={{ width: `${(data.ai.review / aiTotal) * 100}%` }} title="Review" />
            <div className="bg-red-400" style={{ width: `${(data.ai.reject / aiTotal) * 100}%` }} title="Reject" />
          </div>
          <div className="flex gap-4 mt-3 text-xs text-[#8b93ab]">
            <span>● Pass {data.ai.pass}</span>
            <span>● Review {data.ai.review}</span>
            <span>● Reject {data.ai.reject}</span>
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="card p-5">
          <h2 className="font-semibold mb-4">Defects by Type</h2>
          {data.defects.byType.length === 0 ? (
            <p className="text-sm text-[#8b93ab]">No defects detected yet.</p>
          ) : (
            <div className="space-y-3">
              {data.defects.byType.map((d) => (
                <div key={d.key} className="flex items-center gap-3">
                  <span className="w-40 text-xs font-medium text-[#8b93ab] capitalize">{d.key.replace(/_/g, " ")}</span>
                  <div className="flex-1 h-3 rounded-full bg-[#1b2233] overflow-hidden">
                    <div className="h-full rounded-full bg-red-400" style={{ width: `${(d.count / maxDefect) * 100}%` }} />
                  </div>
                  <span className="w-10 text-right text-sm font-medium">{d.count}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card p-5">
          <h2 className="font-semibold mb-4">Operational</h2>
          <ul className="space-y-3 text-sm">
            <li className="flex justify-between">
              <span className="text-[#8b93ab]">Average Inspection Time</span>
              <span className="font-medium">{data.operational.avgInspectionTimeMs !== null ? `${data.operational.avgInspectionTimeMs} ms` : "—"}</span>
            </li>
            <li className="flex justify-between">
              <span className="text-[#8b93ab]">Replacement Rate</span>
              <span className="font-medium">{data.operational.replacementRate}%</span>
            </li>
            <li className="flex justify-between">
              <span className="text-[#8b93ab]">High-Risk Order Rate</span>
              <span className="font-medium">{data.operational.highRiskOrderRate}%</span>
            </li>
            <li className="flex justify-between">
              <span className="text-[#8b93ab]">Delivered Orders</span>
              <span className="font-medium">{data.quality.deliveredOrders}</span>
            </li>
          </ul>
        </div>
      </div>

      <div className="card p-5">
        <h2 className="font-semibold mb-4">Quality Trend (Damage-Free Rate by Day)</h2>
        {data.qualityTrend.length === 0 ? (
          <p className="text-sm text-[#8b93ab]">Not enough delivered/feedback orders yet to show a trend.</p>
        ) : (
          <div className="flex items-end gap-1.5 h-40">
            {data.qualityTrend.map((t) => (
              <div key={t.date} className="flex-1 flex flex-col items-center justify-end gap-1" title={`${t.date}: ${t.damageFreeRate}% (${t.orders} orders)`}>
                <div
                  className="w-full rounded-t bg-[#4f7cff]"
                  style={{ height: `${Math.max(4, (t.damageFreeRate / 100) * 120)}px` }}
                />
                <span className="text-[10px] text-[#5b6480] rotate-0">{t.date.slice(5)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
