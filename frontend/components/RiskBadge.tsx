const STYLES: Record<string, { bg: string; text: string; dot: string }> = {
  LOW: { bg: "bg-emerald-500/15", text: "text-emerald-400", dot: "bg-emerald-400" },
  MEDIUM: { bg: "bg-amber-500/15", text: "text-amber-400", dot: "bg-amber-400" },
  HIGH: { bg: "bg-orange-500/15", text: "text-orange-400", dot: "bg-orange-400" },
  CRITICAL: { bg: "bg-red-500/15", text: "text-red-400", dot: "bg-red-400" },
};

export default function RiskBadge({ level }: { level: string | null | undefined }) {
  if (!level) {
    return <span className="badge bg-white/5 text-[#8b93ab]">Unassessed</span>;
  }
  const style = STYLES[level] || STYLES.LOW;
  return (
    <span className={`badge ${style.bg} ${style.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
      {level}
    </span>
  );
}

export function riskColor(level: string | null | undefined) {
  return (STYLES[level || "LOW"] || STYLES.LOW).text;
}
