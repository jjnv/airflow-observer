import clsx from "clsx";

const stateClass: Record<string, string> = {
  success: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  failed: "bg-red-50 text-red-700 ring-red-200",
  upstream_failed: "bg-red-50 text-red-700 ring-red-200",
  running: "bg-blue-50 text-blue-700 ring-blue-200",
  queued: "bg-slate-50 text-slate-700 ring-slate-200"
};

export function StatusBadge({ state }: { state: string }) {
  return (
    <span
      className={clsx(
        "inline-flex rounded-full px-2 py-1 text-xs font-medium ring-1",
        stateClass[state] || "bg-slate-50 text-slate-700 ring-slate-200"
      )}
    >
      {state}
    </span>
  );
}
