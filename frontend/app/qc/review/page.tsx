"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Inspection } from "@/lib/api";
import InspectionStatusBadge, { ConfidenceLabel } from "@/components/InspectionStatusBadge";
import { LoadingState, ErrorState, EmptyState } from "@/components/States";

export default function QcReviewPage() {
  const [items, setItems] = useState<Inspection[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  function load() {
    api
      .getReviewQueue()
      .then((r) => setItems(r.items))
      .catch((e) => setError(String(e)));
  }

  useEffect(load, []);

  async function decide(inspectionId: number, decision: "accept" | "reject") {
    setBusyId(inspectionId);
    try {
      if (decision === "accept") await api.acceptInspection(inspectionId);
      else await api.rejectInspection(inspectionId);
      load();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusyId(null);
    }
  }

  if (error) return <ErrorState message={error} />;
  if (!items) return <LoadingState label="Loading review queue..." />;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Human Review Queue</h1>
        <p className="text-sm text-[#8b93ab] mt-1">{items.length} product(s) require review</p>
      </div>

      {items.length === 0 && <EmptyState message="Nothing waiting for review right now." />}

      <div className="space-y-3">
        {items.map((insp) => (
          <div key={insp.inspectionId} className="card p-5 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              {insp.image && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}${insp.image.url}`}
                  alt={insp.product.name}
                  className="w-16 h-16 object-cover rounded-lg border border-[#232b40]"
                />
              )}
              <div>
                <div className="font-medium">
                  {insp.product.emoji} {insp.product.name}
                </div>
                <Link href={`/orders/${insp.orderId}`} className="text-xs text-[#4f7cff] hover:underline">
                  {insp.orderCode}
                </Link>
                <div className="text-xs text-[#8b93ab] mt-1">
                  AI Score: {Math.round(insp.qualityScore ?? 0)} · <InspectionStatusBadge status={insp.aiDecision} />
                </div>
                {insp.defects[0] && (
                  <div className="text-xs mt-1">
                    Defect: {insp.defects[0].description} · <ConfidenceLabel confidence={insp.defects[0].confidence} />
                  </div>
                )}
              </div>
            </div>
            <div className="flex gap-2">
              <Link href={`/inspection/${insp.orderId}/${insp.orderItemId}`} className="btn btn-secondary text-xs">
                View Image
              </Link>
              <button
                className="btn btn-primary text-xs"
                disabled={busyId === insp.inspectionId}
                onClick={() => decide(insp.inspectionId, "accept")}
              >
                Accept
              </button>
              <button
                className="btn btn-danger text-xs"
                disabled={busyId === insp.inspectionId}
                onClick={() => decide(insp.inspectionId, "reject")}
              >
                Reject
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
