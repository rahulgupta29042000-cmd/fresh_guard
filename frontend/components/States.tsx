export function LoadingState({ label = "Loading..." }: { label?: string }) {
  return <div className="card p-8 text-center text-[#8b93ab] text-sm">{label}</div>;
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="card p-6 border-red-500/30 bg-red-500/5">
      <div className="font-medium text-red-400 mb-1">Something went wrong</div>
      <div className="text-sm text-[#c3c9dc]">{message}</div>
      <div className="text-xs text-[#8b93ab] mt-3">
        AI risk assessment unavailable — continue with standard fulfillment workflow if this persists.
      </div>
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return <div className="card p-8 text-center text-[#8b93ab] text-sm">{message}</div>;
}
