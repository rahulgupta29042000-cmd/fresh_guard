function bandFor(score: number) {
  if (score >= 90) return { label: "EXCELLENT", color: "#34d399" };
  if (score >= 75) return { label: "GOOD", color: "#60a5fa" };
  if (score >= 60) return { label: "REVIEW", color: "#fbbf24" };
  return { label: "POOR", color: "#f87171" };
}

export default function QualityScoreGauge({ score }: { score: number }) {
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (score / 100) * circumference;
  const band = bandFor(score);

  return (
    <div className="relative w-36 h-36 flex items-center justify-center">
      <svg width="144" height="144" viewBox="0 0 144 144" className="-rotate-90">
        <circle cx="72" cy="72" r="54" fill="none" stroke="#232b40" strokeWidth="12" />
        <circle
          cx="72"
          cy="72"
          r="54"
          fill="none"
          stroke={band.color}
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.6s ease" }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-4xl font-bold">{Math.round(score)}</span>
        <span className="text-xs font-semibold tracking-wide" style={{ color: band.color }}>
          {band.label}
        </span>
      </div>
    </div>
  );
}
