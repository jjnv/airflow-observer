export type Overview = {
  active_dags: number;
  failed_dags_today: number;
  success_rate_7d: number;
  avg_duration_seconds: number;
  p95_duration_seconds: number;
  open_incidents: number;
  agents: AgentStatus[];
  top_recommendations: Recommendation[];
  latest_runs: Array<{
    dag_id: string;
    run_id: string;
    state: string;
    duration_seconds: number | null;
    execution_date: string | null;
  }>;
};

export type DagSummary = {
  dag_id: string;
  owner: string | null;
  tags: string | null;
  is_active: boolean;
  is_paused: boolean;
  latest_state: string;
  latest_duration_seconds: number | null;
  latest_run_id: string | null;
};

export type Incident = {
  id?: number;
  dag_id: string;
  task_id: string | null;
  title: string;
  severity: string;
  status?: string;
  error_summary: string | null;
  consecutive_failures: number;
  last_seen_at: string;
};

export type Recommendation = {
  id?: number;
  dag_id: string;
  task_id: string | null;
  kind: string;
  title: string;
  impact: string;
  reason: string;
  evidence_count: number;
  estimated_savings_seconds: number | null;
  score: number;
  status?: string;
};

export type AgentStatus = {
  airflow_instance_uid: string;
  name: string;
  base_url: string | null;
  agent_version: string | null;
  last_heartbeat_at: string | null;
  seconds_since_seen?: number | null;
  status?: string;
  last_snapshot: {
    dags: number;
    dag_runs: number;
    task_runs: number;
  };
};

export type Onboarding = {
  workspace_id: string;
  api_key_env_var: string;
  steps: string[];
  docker_command: string;
  docker_compose_service: {
    build: string;
    environment: Record<string, string>;
  };
};

export type AlertChannel = {
  id: number;
  workspace_id: string;
  kind: string;
  name: string;
  is_enabled: boolean;
  target_preview: string;
  created_at: string;
};

export type DagDetail = {
  dag: DagSummary;
  runs: Array<{
    run_id: string;
    state: string;
    start_time: string | null;
    end_time: string | null;
    execution_date: string | null;
    duration_seconds: number | null;
    tasks: Array<{
      task_id: string;
      state: string;
      try_number: number;
      duration_seconds: number | null;
      error_summary: string | null;
    }>;
  }>;
  incidents: Incident[];
  recommendations: Recommendation[];
};

const API_URL = process.env.OBSERVER_API_URL || "http://localhost:8000";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Observer API returned ${response.status} for ${path}`);
  }
  return response.json();
}

export function getOverview() {
  return getJson<Overview>("/api/v1/overview");
}

export function getDags() {
  return getJson<{ dags: DagSummary[] }>("/api/v1/dags");
}

export function getDagDetail(dagId: string) {
  return getJson<DagDetail>(`/api/v1/dags/${encodeURIComponent(dagId)}`);
}

export function getIncidents() {
  return getJson<{ incidents: Incident[] }>("/api/v1/incidents");
}

export function getRecommendations() {
  return getJson<{ recommendations: Recommendation[] }>("/api/v1/recommendations");
}

export function getAgentStatus() {
  return getJson<{ agents: AgentStatus[] }>("/api/v1/agent/status");
}

export function getOnboarding() {
  return getJson<Onboarding>("/api/v1/onboarding");
}

export function getAlertChannels() {
  return getJson<{ channels: AlertChannel[] }>("/api/v1/alert-channels");
}

export function seconds(value: number | null | undefined) {
  if (!value) return "0s";
  if (value < 60) return `${Math.round(value)}s`;
  return `${Math.round(value / 60)}m`;
}

export function relativeSeconds(value: number | null | undefined) {
  if (value === null || value === undefined) return "never";
  if (value < 60) return `${Math.round(value)}s ago`;
  if (value < 3600) return `${Math.round(value / 60)}m ago`;
  return `${Math.round(value / 3600)}h ago`;
}
