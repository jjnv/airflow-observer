import { PageError } from "@/components/page-state";
import { getAlertChannels } from "@/lib/api";

export default async function AlertsPage() {
  let data: Awaited<ReturnType<typeof getAlertChannels>>;
  try {
    data = await getAlertChannels();
  } catch (error) {
    return <PageError title="Alerts are unavailable" message={error instanceof Error ? error.message : undefined} />;
  }
  const { channels } = data;

  return (
    <div className="space-y-6">
      <section>
        <p className="text-sm text-muted">Slack routing</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight">Alerts</h1>
      </section>

      <section className="card p-4">
        <h2 className="font-semibold">Configured channels</h2>
        <div className="mt-4 space-y-3">
          {channels.map((channel) => (
            <div key={channel.id} className="rounded-md border border-border p-3">
              <div className="flex items-center justify-between gap-3">
                <div className="font-medium">{channel.name}</div>
                <span className="rounded-full bg-blue-50 px-2 py-1 text-xs font-medium uppercase text-blue-700 ring-1 ring-blue-200">
                  {channel.is_enabled ? "enabled" : "disabled"}
                </span>
              </div>
              <p className="mt-1 text-sm text-muted">
                {channel.kind} · {channel.target_preview}
              </p>
            </div>
          ))}
          {channels.length === 0 ? <p className="text-sm text-muted">No Slack channels configured yet.</p> : null}
        </div>
      </section>

      <section className="card p-4">
        <h2 className="font-semibold">Create a Slack channel</h2>
        <p className="mt-2 text-sm text-muted">
          Keep webhooks out of the browser for now. Add the channel from your terminal with the demo API key.
        </p>
        <pre className="mt-4 overflow-x-auto rounded-md bg-slate-950 p-4 text-sm text-slate-50">
{`curl -X POST http://localhost:8000/api/v1/alert-channels \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: <your-observer-api-key>" \\
  -d "{\\"kind\\":\\"slack\\",\\"name\\":\\"Data alerts\\",\\"target\\":\\"https://hooks.slack.com/services/...\\",\\"is_enabled\\":true}"`}
        </pre>
      </section>
    </div>
  );
}
