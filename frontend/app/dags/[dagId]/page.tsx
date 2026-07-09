import { RuntimeLineChart, TaskDurationBarChart } from "@/components/charts";
import { PageError } from "@/components/page-state";
import { StatusBadge } from "@/components/status-badge";
import { getDagDetail, seconds } from "@/lib/api";

export default async function DagDetailPage({ params }: { params: Promise<{ dagId: string }> }) {
  const { dagId } = await params;
  let detail: Awaited<ReturnType<typeof getDagDetail>>;
  try {
    detail = await getDagDetail(decodeURIComponent(dagId));
  } catch (error) {
    return <PageError title="DAG detail is unavailable" message={error instanceof Error ? error.message : undefined} />;
  }
  const chartData = [...detail.runs]
    .reverse()
    .map((run) => ({
      label: run.execution_date ? new Date(run.execution_date).toLocaleDateString() : run.run_id.slice(0, 12),
      duration: Math.round(run.duration_seconds || 0)
    }));
  const latestRun = detail.runs[0];
  const taskData =
    latestRun?.tasks.map((task) => ({
      task: task.task_id,
      duration: Math.round(task.duration_seconds || 0)
    })) || [];

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm text-muted">DAG detail</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">{detail.dag.dag_id}</h1>
          <p className="mt-2 text-sm text-muted">Owner: {detail.dag.owner || "Unassigned"}</p>
        </div>
        {latestRun ? <StatusBadge state={latestRun.state} /> : null}
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="card p-4">
          <h2 className="mb-4 font-semibold">Runtime history</h2>
          <RuntimeLineChart data={chartData} />
        </div>
        <div className="card p-4">
          <h2 className="mb-4 font-semibold">Latest task duration</h2>
          <TaskDurationBarChart data={taskData} />
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="card p-4">
          <h2 className="font-semibold">Open incidents</h2>
          <div className="mt-4 space-y-3">
            {detail.incidents.map((incident) => (
              <div key={`${incident.title}-${incident.task_id}`} className="rounded-md border border-border p-3">
                <div className="font-medium">{incident.title}</div>
                <div className="mt-1 text-sm text-muted">
                  {incident.task_id || "DAG"} failed {incident.consecutive_failures} times consecutively.
                </div>
                {incident.error_summary ? <div className="mt-2 text-sm">{incident.error_summary}</div> : null}
              </div>
            ))}
            {detail.incidents.length === 0 ? <p className="text-sm text-muted">No open incidents.</p> : null}
          </div>
        </div>
        <div className="card p-4">
          <h2 className="font-semibold">Recommendations</h2>
          <div className="mt-4 space-y-3">
            {detail.recommendations.map((recommendation) => (
              <div key={`${recommendation.title}-${recommendation.task_id}`} className="rounded-md border border-border p-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="font-medium">{recommendation.title}</div>
                  <div className="text-xs uppercase text-muted">{recommendation.impact}</div>
                </div>
                <p className="mt-1 text-sm text-muted">{recommendation.reason}</p>
                <p className="mt-2 text-xs text-muted">
                  Evidence: {recommendation.evidence_count} · Estimated saving:{" "}
                  {seconds(recommendation.estimated_savings_seconds)}
                </p>
              </div>
            ))}
            {detail.recommendations.length === 0 ? <p className="text-sm text-muted">No recommendations yet.</p> : null}
          </div>
        </div>
      </section>

      <section className="card overflow-hidden">
        <div className="border-b border-border px-4 py-3">
          <h2 className="font-semibold">Recent runs</h2>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-surface text-left text-muted">
            <tr>
              <th className="px-4 py-3 font-medium">Run</th>
              <th className="px-4 py-3 font-medium">State</th>
              <th className="px-4 py-3 font-medium">Duration</th>
            </tr>
          </thead>
          <tbody>
            {detail.runs.map((run) => (
              <tr key={run.run_id} className="border-t border-border">
                <td className="px-4 py-3">{run.run_id}</td>
                <td className="px-4 py-3">
                  <StatusBadge state={run.state} />
                </td>
                <td className="px-4 py-3">{seconds(run.duration_seconds)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
