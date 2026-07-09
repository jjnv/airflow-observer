import Link from "next/link";

import { PageError } from "@/components/page-state";
import { getIncidents } from "@/lib/api";

export default async function IncidentsPage() {
  let data: Awaited<ReturnType<typeof getIncidents>>;
  try {
    data = await getIncidents();
  } catch (error) {
    return <PageError title="Incidents are unavailable" message={error instanceof Error ? error.message : undefined} />;
  }
  const { incidents } = data;

  return (
    <div className="space-y-6">
      <section>
        <p className="text-sm text-muted">Grouped failures</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight">Incidents</h1>
      </section>

      <section className="grid gap-3">
        {incidents.map((incident) => (
          <article key={incident.id} className="card p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <Link className="font-semibold text-accent hover:underline" href={`/dags/${encodeURIComponent(incident.dag_id)}`}>
                  {incident.title}
                </Link>
                <p className="mt-1 text-sm text-muted">
                  {incident.dag_id}
                  {incident.task_id ? ` / ${incident.task_id}` : ""} · {incident.consecutive_failures} consecutive failures
                </p>
              </div>
              <span className="rounded-full bg-red-50 px-2 py-1 text-xs font-medium text-red-700 ring-1 ring-red-200">
                {incident.severity}
              </span>
            </div>
            {incident.error_summary ? <p className="mt-3 text-sm">{incident.error_summary}</p> : null}
          </article>
        ))}
        {incidents.length === 0 ? <div className="card p-6 text-sm text-muted">No incidents found.</div> : null}
      </section>
    </div>
  );
}
