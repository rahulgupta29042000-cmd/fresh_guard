"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";

const ISSUE_OPTIONS = [
  { value: "none", label: "✓ No issue" },
  { value: "bruised_damaged_produce", label: "⚠ Bruised / damaged produce" },
  { value: "crushed_packaging", label: "📦 Crushed packaging" },
  { value: "broken_item", label: "💔 Broken item" },
  { value: "temperature_issue", label: "🌡 Temperature issue" },
  { value: "spoiled_product", label: "🍎 Spoiled product" },
  { value: "other", label: "Other" },
];

export default function FeedbackPage() {
  const params = useParams();
  const orderId = Number(params.orderId);
  const [issueType, setIssueType] = useState("none");
  const [rating, setRating] = useState<number | null>(null);
  const [comments, setComments] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [checking, setChecking] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api
      .getFeedback(orderId)
      .then((fb) => {
        if (fb) setSubmitted(true);
      })
      .catch(() => {})
      .finally(() => setChecking(false));
  }, [orderId]);

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      await api.submitFeedback(orderId, { rating: rating ?? undefined, issue_type: issueType, comments: comments || undefined });
      setSubmitted(true);
    } catch (e) {
      setError(String(e));
    } finally {
      setSubmitting(false);
    }
  }

  if (checking) {
    return <div className="max-w-lg mx-auto card p-8 text-center text-[#8b93ab] text-sm">Loading...</div>;
  }

  if (submitted) {
    return (
      <div className="max-w-lg mx-auto card p-8 text-center space-y-3">
        <div className="text-3xl">✅</div>
        <h1 className="text-xl font-bold">Thanks for your feedback!</h1>
        <p className="text-sm text-[#8b93ab]">This helps Fresh_Guard improve future risk predictions.</p>
        <Link href="/dashboard" className="btn btn-primary inline-flex mt-3">
          Back to Dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto space-y-6">
      <h1 className="text-2xl font-bold">Customer Feedback</h1>
      <div className="card p-6 space-y-5">
        <div>
          <p className="font-medium mb-3">Did you experience any quality or damage issue?</p>
          <div className="space-y-2">
            {ISSUE_OPTIONS.map((opt) => (
              <label
                key={opt.value}
                className={`flex items-center gap-2 p-3 rounded-lg border cursor-pointer text-sm ${
                  issueType === opt.value ? "border-[#4f7cff] bg-[#1a2136]" : "border-[#232b40]"
                }`}
              >
                <input
                  type="radio"
                  name="issue"
                  value={opt.value}
                  checked={issueType === opt.value}
                  onChange={() => setIssueType(opt.value)}
                />
                {opt.label}
              </label>
            ))}
          </div>
        </div>

        <div>
          <p className="font-medium mb-2 text-sm">Rating (optional)</p>
          <div className="flex gap-2">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setRating(n)}
                className={`w-10 h-10 rounded-lg border text-sm font-semibold ${
                  rating === n ? "border-[#4f7cff] bg-[#1a2136]" : "border-[#232b40] text-[#8b93ab]"
                }`}
              >
                {n}
              </button>
            ))}
          </div>
        </div>

        <div>
          <p className="font-medium mb-2 text-sm">Comments (optional)</p>
          <textarea
            className="w-full bg-[#0f1420] border border-[#232b40] rounded-lg p-3 text-sm"
            rows={3}
            value={comments}
            onChange={(e) => setComments(e.target.value)}
            placeholder="Tell us more..."
          />
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <button className="btn btn-primary w-full" onClick={submit} disabled={submitting}>
          {submitting ? "Submitting..." : "Submit Feedback"}
        </button>
      </div>
    </div>
  );
}
