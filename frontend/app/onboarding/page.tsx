import { PageError } from "@/components/page-state";
import { getAgentStatus, getOnboarding, relativeSeconds } from "@/lib/api";

export default async function OnboardingPage() {
  let data: [Awaited<ReturnType<typeof getOnboarding>>, Awaited<ReturnType<typeof getAgentStatus>>];
  try {
    data = await Promise.all([getOnboarding(), getAgentStatus()]);
  } catch (error) {
    return <PageError title="Onboarding is unavailable" message={error instanceof Error ? error.message : undefined} />;
  }
  const [onboarding, status] = data;
  const envLines = Object.entries(onboarding.docker_compose_service.environment)
    .map(([key, value]) => `      ${key}: ${value}`)
    .join("\n");

  return (
    <div className="space-y-6">
      <section>
        <p className="text-sm text-muted">Install the collector</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight">Agent onboarding</h1>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="card p-4">
          <h2 className="font-semibold">Setup steps</h2>
          <ol className="mt-4 list-decimal space-y-2 pl-5 text-sm text-muted">
            {onboarding.steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </div>
        <div className="card p-4">
          <h2 className="font-semibold">Connected agents</h2>
          <div className="mt-4 space-y-3">
            {status.agents.map((agent) => (
              <div key={agent.airflow_instance_uid} className="rounded-md border border-border p-3">
                <div className="font-medium">{agent.name}</div>
                <p className="mt-1 text-sm text-muted">
                  Last heartbeat: {relativeSeconds(agent.seconds_since_seen)} · Version: {agent.agent_version || "unknown"}
                </p>
                <p className="mt-1 text-xs text-muted">
                  Latest snapshot: {agent.last_snapshot.dags} DAGs, {agent.last_snapshot.dag_runs} runs,{" "}
                  {agent.last_snapshot.task_runs} tasks
                </p>
              </div>
            ))}
            {status.agents.length === 0 ? <p className="text-sm text-muted">No agent has connected yet.</p> : null}
          </div>
        </div>
      </section>

      <section className="card p-4">
        <h2 className="font-semibold">Docker Compose service</h2>
        <pre className="mt-4 overflow-x-auto rounded-md bg-slate-950 p-4 text-sm text-slate-50">
{`agent:
  build: ${onboarding.docker_compose_service.build}
  environment:
${envLines}`}
        </pre>
      </section>

      <section className="card p-4">
        <h2 className="font-semibold">API key</h2>
        <p className="mt-2 text-sm text-muted">
          Workspace: <code>{onboarding.workspace_id}</code>. Set the backend key with{" "}
          <code>DEFAULT_API_KEY</code> and pass the same value to the agent as{" "}
          <code>{onboarding.api_key_env_var}</code>.
        </p>
      </section>
    </div>
  );
}
