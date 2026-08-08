const STYLES: Record<string, { bg: string; text: string; dot: string }> = {
  PASS: { bg: "bg-emerald-500/15", text: "text-emerald-400", dot: "bg-emerald-400" },
  REVIEW: { bg: "bg-amber-500/15", text: "text-amber-400", dot: "bg-amber-400" },
  REJECT: { bg: "bg-red-500/15", text: "text-red-400", dot: "bg-red-400" },
  PENDING: { bg: "bg-white/5", text: "text-[#8b93ab]", dot: "bg-[#8b93ab]" },
};

export default function InspectionStatusBadge({ status }: { status: string | null | undefined }) {
  const style = STYLES[status || "PENDING"] || STYLES.PENDING;
  return (
    <span className={`badge ${style.bg} ${style.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
      {status || "PENDING"}
    </span>
  );
}

// Confidence is shown as High/Medium/Low, never a bare percentage presented
// as certainty — per the Phase 2 brief's explainability requirement.
export function ConfidenceLabel({ confidence }: { confidence: number }) {
  const label = confidence >= 0.8 ? "High" : confidence >= 0.6 ? "Medium" : "Low";
  const color = confidence >= 0.8 ? "text-red-400" : confidence >= 0.6 ? "text-amber-400" : "text-[#8b93ab]";
  return (
    <span className={color}>
      {label} confidence <span className="text-[#5b6480]">({Math.round(confidence * 100)}%)</span>
    </span>
  );
}
