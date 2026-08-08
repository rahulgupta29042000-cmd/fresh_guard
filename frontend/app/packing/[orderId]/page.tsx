"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { LoadingState, ErrorState } from "@/components/States";

type Bag = { bag_name: string; category: string; items: { order_item_id: number; name: string }[] };
type Plan = { order_id: number; status: string; notes: string | null; bags: Bag[] };

export default function PackingPage() {
  const params = useParams();
  const orderId = Number(params.orderId);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [draftBags, setDraftBags] = useState<Bag[]>([]);
  const [issueNote, setIssueNote] = useState("");
  const [showIssueForm, setShowIssueForm] = useState(false);

  function load() {
    api
      .getPackingPlan(orderId)
      .then((p) => {
        setPlan(p);
        setDraftBags(p.bags);
      })
      .catch((e) => setError(String(e)));
  }

  useEffect(load, [orderId]);

  async function confirm() {
    try {
      await api.packingAction(orderId, "confirm");
      load();
    } catch (e) {
      setError(String(e));
    }
  }

  async function saveModifications() {
    try {
      await api.packingAction(orderId, "modify", draftBags);
      setEditing(false);
      load();
    } catch (e) {
      setError(String(e));
    }
  }

  async function reportIssue() {
    try {
      await api.packingAction(orderId, "report_issue", undefined, issueNote);
      setShowIssueForm(false);
      setIssueNote("");
      load();
    } catch (e) {
      setError(String(e));
    }
  }

  function moveItem(orderItemId: number, fromBagIdx: number, toBagName: string) {
    setDraftBags((bags) => {
      const copy = bags.map((b) => ({ ...b, items: [...b.items] }));
      const [moving] = copy[fromBagIdx].items.splice(
        copy[fromBagIdx].items.findIndex((i) => i.order_item_id === orderItemId),
        1
      );
      let target = copy.find((b) => b.bag_name === toBagName);
      if (!target) {
        target = { bag_name: toBagName, category: toBagName, items: [] };
        copy.push(target);
      }
      target.items.push(moving);
      return copy.filter((b) => b.items.length > 0);
    });
  }

  if (error) return <ErrorState message={error} />;
  if (!plan) return <LoadingState label="Loading packing plan..." />;

  const allBagNames = ["FRAGILE", "COLD / TEMPERATURE-PROTECTED", "PRODUCE", "LIGHTWEIGHT", "GENERAL"];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold">Packing Plan</h1>
          <p className="text-sm text-[#8b93ab] mt-1">
            Order {plan.order_id} · Status: <span className="capitalize">{plan.status.replace("_", " ")}</span>
          </p>
        </div>
        <Link href={`/orders/${orderId}`} className="text-sm text-[#4f7cff] hover:underline">
          ← Back to order
        </Link>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {(editing ? draftBags : plan.bags).map((bag, bagIdx) => (
          <div key={bag.bag_name} className="card p-5">
            <h3 className="font-semibold text-sm mb-3">BAG {bagIdx + 1} — {bag.bag_name}</h3>
            <ul className="space-y-2">
              {bag.items.map((item) => (
                <li key={item.order_item_id} className="flex items-center justify-between text-sm">
                  <span>{item.name}</span>
                  {editing && (
                    <select
                      className="bg-[#0f1420] border border-[#232b40] rounded px-2 py-1 text-xs"
                      value={bag.bag_name}
                      onChange={(e) => moveItem(item.order_item_id, bagIdx, e.target.value)}
                    >
                      {allBagNames.map((n) => (
                        <option key={n} value={n}>
                          {n}
                        </option>
                      ))}
                    </select>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {plan.notes && (
        <div className="card p-4 border-red-500/30 bg-red-500/5 text-sm">
          <span className="text-red-400 font-medium">Reported issue:</span> {plan.notes}
        </div>
      )}

      <div className="flex flex-wrap gap-3">
        {!editing ? (
          <>
            <button className="btn btn-primary" onClick={confirm}>
              Confirm Recommendation
            </button>
            <button className="btn btn-secondary" onClick={() => setEditing(true)}>
              Modify Packing
            </button>
            <button className="btn btn-secondary" onClick={() => setShowIssueForm((s) => !s)}>
              Report Packing Issue
            </button>
          </>
        ) : (
          <>
            <button className="btn btn-primary" onClick={saveModifications}>
              Save Changes
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => {
                setEditing(false);
                setDraftBags(plan.bags);
              }}
            >
              Cancel
            </button>
          </>
        )}
      </div>

      {showIssueForm && (
        <div className="card p-4 space-y-3">
          <textarea
            className="w-full bg-[#0f1420] border border-[#232b40] rounded-lg p-3 text-sm"
            rows={3}
            placeholder="Describe the packing issue..."
            value={issueNote}
            onChange={(e) => setIssueNote(e.target.value)}
          />
          <button className="btn btn-danger" onClick={reportIssue}>
            Submit Issue Report
          </button>
        </div>
      )}
    </div>
  );
}
