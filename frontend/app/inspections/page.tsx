"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Inspection } from "@/lib/api";
import InspectionStatusBadge from "@/components/InspectionStatusBadge";
import { LoadingState, ErrorState, EmptyState } from "@/components/States";

const STATUSES = ["PASS", "REVIEW", "REJECT"];

export default function InspectionsPage() {
  const [inspections, setInspections] = useState<Inspection[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState("");
  const [date, setDate] = useState("");

  function load() {
    const params: Record<string, string> = { limit: "50" };
    if (status) params.status = status;
    if (date) params.date = date;
    api
      .listInspections(params)
      .then(setInspections)
      .catch((e) => setError(String(e)));
  }

  useEffect(load, [status, date]);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold">Inspection History</h1>
          <p className="text-sm text-[#8b93ab] mt-1">Showing the most recent 50 matching inspections.</p>
        </div>
        <Link href="/qc/review" className="text-sm text-[#4f7cff] hover:underline">
          Human Review Queue →
        </Link>
      </div>

      <div className="flex flex-wrap gap-3">
        <select className="bg-[#161c2c] border border-[#232b40] rounded-lg px-3 py-2 text-sm" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All results</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <input
          type="date"
          className="bg-[#161c2c] border border-[#232b40] rounded-lg px-3 py-2 text-sm"
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />
      </div>

      {error && <ErrorState message={error} />}
      {!error && !inspections && <LoadingState label="Loading inspections..." />}
      {!error && inspections && inspections.length === 0 && <EmptyState message="No inspections match these filters." />}

      {!error && inspections && inspections.length > 0 && (
        <div className="card overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Inspection</th>
                <th>Order</th>
                <th>Product</th>
                <th>Quality Score</th>
                <th>Defect</th>
                <th>AI Decision</th>
                <th>Human Decision</th>
                <th>Model</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {inspections.map((insp) => (
                <tr key={insp.inspectionId}>
                  <td>
                    <Link href={`/inspection/${insp.orderId}/${insp.orderItemId}`} className="text-[#4f7cff] hover:underline">
                      INS-{insp.inspectionId}
                    </Link>
                  </td>
                  <td>{insp.orderCode}</td>
                  <td>
                    {insp.product.emoji} {insp.product.name}
                  </td>
                  <td>{insp.qualityScore !== null ? Math.round(insp.qualityScore) : "—"}</td>
                  <td>{insp.defects[0]?.description || "—"}</td>
                  <td>
                    <InspectionStatusBadge status={insp.aiDecision} />
                  </td>
                  <td className="text-[#8b93ab]">{insp.humanDecision || "—"}</td>
                  <td className="text-[#8b93ab] text-xs">{insp.modelVersion}</td>
                  <td className="text-[#8b93ab]">{new Date(insp.createdAt).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
