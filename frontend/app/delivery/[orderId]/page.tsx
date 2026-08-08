"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { LoadingState, ErrorState } from "@/components/States";

type DeliveryInfo = {
  order_id: number;
  instructions: string[];
  fragile_item_count: number;
  temperature_sensitive_item_count: number;
  accepted: boolean;
  accepted_at: string | null;
};

export default function DeliveryPage() {
  const params = useParams();
  const orderId = Number(params.orderId);
  const [info, setInfo] = useState<DeliveryInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [delivered, setDelivered] = useState(false);

  function load() {
    api
      .getDeliveryInstructions(orderId)
      .then(setInfo)
      .catch((e) => setError(String(e)));
  }

  useEffect(load, [orderId]);

  async function accept() {
    try {
      await api.deliveryAction(orderId, "accept_instructions");
      load();
    } catch (e) {
      setError(String(e));
    }
  }

  async function markDelivered() {
    try {
      await api.deliveryAction(orderId, "mark_delivered");
      setDelivered(true);
    } catch (e) {
      setError(String(e));
    }
  }

  if (error) return <ErrorState message={error} />;
  if (!info) return <LoadingState label="Loading delivery instructions..." />;

  const isSpecial = info.fragile_item_count > 0 || info.temperature_sensitive_item_count > 0;

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Delivery Handling</h1>
        <Link href={`/orders/${orderId}`} className="text-sm text-[#4f7cff] hover:underline">
          ← Back to order
        </Link>
      </div>

      <div className="card p-6 space-y-4">
        {isSpecial && (
          <div className="text-orange-400 font-semibold text-sm">⚠️ FRAGILE / TEMPERATURE-SENSITIVE ORDER</div>
        )}
        <div className="text-sm text-[#c3c9dc] space-y-1">
          {info.fragile_item_count > 0 && <p>{info.fragile_item_count} fragile item(s)</p>}
          {info.temperature_sensitive_item_count > 0 && <p>{info.temperature_sensitive_item_count} temperature-sensitive item(s)</p>}
          {!isSpecial && <p>No special handling flags for this order.</p>}
        </div>

        <div>
          <div className="text-xs uppercase tracking-wide text-[#8b93ab] font-medium mb-2">Instructions</div>
          <ul className="space-y-1.5 text-sm">
            {info.instructions.map((instr, i) => (
              <li key={i}>✓ {instr}</li>
            ))}
          </ul>
        </div>

        <div className="pt-2 flex gap-3">
          {!info.accepted ? (
            <button className="btn btn-primary" onClick={accept}>
              Accept Handling Instructions
            </button>
          ) : !delivered ? (
            <>
              <span className="text-emerald-400 text-sm self-center">✓ Instructions accepted — dispatched</span>
              <button className="btn btn-primary" onClick={markDelivered}>
                Mark Delivered
              </button>
            </>
          ) : (
            <div className="space-y-2">
              <span className="text-emerald-400 text-sm block">✓ Delivered</span>
              <Link href={`/feedback/${orderId}`} className="btn btn-primary inline-flex">
                Collect Customer Feedback
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
