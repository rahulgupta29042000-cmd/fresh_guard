export default function StatCard({
  label,
  value,
  change,
  changeGood,
  subtitle,
}: {
  label: string;
  value: string;
  change?: string;
  changeGood?: boolean;
  subtitle?: string;
}) {
  return (
    <div className="card p-5">
      <div className="text-xs uppercase tracking-wide text-[#8b93ab] font-medium">{label}</div>
      <div className="mt-2 text-3xl font-bold">{value}</div>
      {change !== undefined && (
        <div className={`mt-1 text-xs font-medium ${changeGood ? "text-emerald-400" : "text-red-400"}`}>
          {change}
        </div>
      )}
      {subtitle && <div className="mt-1 text-xs text-[#8b93ab]">{subtitle}</div>}
    </div>
  );
}
