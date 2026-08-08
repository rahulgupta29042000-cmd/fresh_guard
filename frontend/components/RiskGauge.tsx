import { riskColor } from "./RiskBadge";

export default function RiskGauge({ score, level }: { score: number; level: string }) {
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (score / 100) * circumference;
  const colorClass = riskColor(level);
  const strokeColor: Record<string, string> = {
    "text-emerald-400": "#34d399",
    "text-amber-400": "#fbbf24",
    "text-orange-400": "#fb923c",
    "text-red-400": "#f87171",
  };

  return (
    <div className="relative w-36 h-36 flex items-center justify-center">
      <svg width="144" height="144" viewBox="0 0 144 144" className="-rotate-90">
        <circle cx="72" cy="72" r="54" fill="none" stroke="#232b40" strokeWidth="12" />
        <circle
          cx="72"
          cy="72"
          r="54"
          fill="none"
          stroke={strokeColor[colorClass] || "#4f7cff"}
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.6s ease" }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-4xl font-bold">{score}</span>
        <span className={`text-xs font-semibold tracking-wide ${colorClass}`}>{level} RISK</span>
      </div>
    </div>
  );
}
