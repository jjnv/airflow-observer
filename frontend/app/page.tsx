import Link from "next/link";

import { MetricCard } from "@/components/metric-card";
import { PageError } from "@/components/page-state";
import { StatusBadge } from "@/components/status-badge";
import { getDags, getOverview, relativeSeconds, seconds } from "@/lib/api";

export default async function OverviewPage() {
  let data: [Awaited<ReturnType<typeof getOverview>>, Awaited<ReturnType<typeof getDags>>];
  try {
    data = await Promise.all([getOverview(), getDags()]);
  } catch (error) {
    return <PageError title="Overview is unavailable" message={error instanceof Error ? error.message : undefined} />;
  }
  const [overview, dags] = data;

  return (
    <div className="space-y-6">
      <section>
        <p className="text-sm font-medium text-accent">Prioritized Airflow fixes</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight">What needs attention today?</h1>
      </section>

      <section className="grid gap-4 md:grid-cols-3 lg:grid-cols-6">
        <MetricCard label="Active DAGs" value={overview.active_dags} />
        <MetricCard label="Failed DAGs" value={overview.failed_dags_today} detail="Latest observed runs" />
        <MetricCard label="Success Rate" value={`${overview.success_rate_7d}%`} detail="Recent runs" />
        <MetricCard label="Avg Duration" value={seconds(overview.avg_duration_seconds)} />
        <MetricCard label="p95 Duration" value={seconds(overview.p95_duration_seconds)} />
        <MetricCard label="Open Incidents" value={overview.open_incidents} />
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <div className="card p-4 lg:col-span-2">
          <div className="flex items-center justify-between gap-3">
            <h2 className="font-semibold">Top fixes today</h2>
            <Link className="text-sm text-accent hover:underline" href="/recommendations">
              View all
            </Link>
          </div>
          <div className="mt-4 space-y-3">
            {overview.top_recommendations.map((item, index) => (
              <Link
                key={`${item.kind}-${item.dag_id}-${item.task_id || "dag"}`}
                href={`/dags/${encodeURIComponent(item.dag_id)}`}
                className="block rounded-md border border-border p-3 hover:border-accent"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="font-medium">
                    #{index + 1} {item.title}
                  </div>
                  <span className="rounded-full bg-blue-50 px-2 py-1 text-xs font-medium uppercase text-blue-700 ring-1 ring-blue-200">
                    {item.impact}
                  </span>
                </div>
                <p className="mt-1 text-sm text-muted">{item.reason}</p>
                <p className="mt-2 text-xs text-muted">
                  Evidence: {item.evidence_count} · Estimated saving: {seconds(item.estimated_savings_seconds)}
                </p>
              </Link>
            ))}
            {overview.top_recommendations.length === 0 ? <p className="text-sm text-muted">No fixes detected yet.</p> : null}
          </div>
        </div>

        <div className="card p-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="font-semibold">Agent status</h2>
            <Link className="text-sm text-accent hover:underline" href="/onboarding">
              Setup
            </Link>
          </div>
          <div className="mt-4 space-y-3">
            {overview.agents.map((agent) => (
              <div key={agent.airflow_instance_uid} className="rounded-md border border-border p-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="font-medium">{agent.name}</div>
                  <span className="rounded-full bg-emerald-50 px-2 py-1 text-xs font-medium uppercase text-emerald-700 ring-1 ring-emerald-200">
                    {agent.status || "seen"}
                  </span>
                </div>
                <p className="mt-1 text-sm text-muted">
                  Last heartbeat: {relativeSeconds(agent.seconds_since_seen)}
                </p>
                <p className="mt-1 text-xs text-muted">
                  Snapshot: {agent.last_snapshot.dags} DAGs, {agent.last_snapshot.dag_runs} runs,{" "}
                  {agent.last_snapshot.task_runs} tasks
                </p>
              </div>
            ))}
            {overview.agents.length === 0 ? <p className="text-sm text-muted">No agent has connected yet.</p> : null}
          </div>
        </div>
      </section>

      <section className="card overflow-hidden">
        <div className="border-b border-border px-4 py-3">
          <h2 className="font-semibold">DAG health</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="bg-surface text-left text-muted">
              <tr>
                <th className="px-4 py-3 font-medium">DAG</th>
                <th className="px-4 py-3 font-medium">Owner</th>
                <th className="px-4 py-3 font-medium">State</th>
                <th className="px-4 py-3 font-medium">Latest Duration</th>
                <th className="px-4 py-3 font-medium">Paused</th>
              </tr>
            </thead>
            <tbody>
              {dags.dags.map((dag) => (
                <tr key={dag.dag_id} className="border-t border-border">
                  <td className="px-4 py-3 font-medium">
                    <Link className="text-accent hover:underline" href={`/dags/${encodeURIComponent(dag.dag_id)}`}>
                      {dag.dag_id}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-muted">{dag.owner || "Unassigned"}</td>
                  <td className="px-4 py-3">
                    <StatusBadge state={dag.latest_state} />
                  </td>
                  <td className="px-4 py-3">{seconds(dag.latest_duration_seconds)}</td>
                  <td className="px-4 py-3">{dag.is_paused ? "Yes" : "No"}</td>
                </tr>
              ))}
              {dags.dags.length === 0 ? (
                <tr>
                  <td className="px-4 py-6 text-muted" colSpan={5}>
                    No Airflow snapshots have been ingested yet.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
