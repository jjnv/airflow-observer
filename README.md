# Airflow Observer

Open source, self-hosted observability for Apache Airflow.

Airflow Observer helps small data teams answer one daily operational question:

> Which DAGs need attention today, and why?

It collects Airflow metadata through the stable REST API, ingests snapshots into a FastAPI backend, stores them in Postgres, computes incidents and recommendations, and presents the result in a Next.js dashboard.

## Highlights

- Self-hosted by default with Docker Compose and local image builds.
- No SaaS account, hosted image registry, billing, SSO, or vendor lock-in.
- Agent-based collection from your Airflow REST API.
- API-key protected ingestion.
- Postgres persistence for DAGs, runs, task runs, incidents, recommendations, alert channels, and agent status.
- Operational recommendations for repeated failures, runtime anomalies, slow tasks, excessive retries, missing owners, and missing tags.
- Demo mode with local Airflow, synthetic DAGs, and seeded history.

## Architecture

```text
Your Airflow
  |
  | REST API
  v
Airflow Observer Agent
  |
  | POST /api/v1/ingest/snapshot
  v
FastAPI Backend
  |
  v
Postgres
  |
  v
Next.js Dashboard
```

## Requirements

- Docker and Docker Compose v2.
- An Airflow instance with REST API access.
- Airflow Basic auth credentials or a bearer token.
- A strong Observer API key shared by the backend and agent.

## Try The Demo

The demo starts Postgres, backend, frontend, a local Airflow instance, sample DAGs, an agent, and a seeded dataset.

```powershell
docker compose --env-file .env.demo -f docker-compose.yml -f docker-compose.demo.yml up --build
```

Open:

- Dashboard: http://localhost:3000
- Backend API docs: http://localhost:8000/docs
- Airflow: http://localhost:8080

Demo Airflow credentials:

```text
username: admin
password: admin
```

Stop and remove demo data:

```powershell
docker compose --env-file .env.demo -f docker-compose.yml -f docker-compose.demo.yml down -v
```

## Self-Hosted Setup

Copy the example environment file and replace every `replace-...` value.

PowerShell:

```powershell
Copy-Item .env.example .env
notepad .env
docker compose --env-file .env config --quiet
docker compose --env-file .env up --build
```

POSIX shell:

```bash
cp .env.example .env
$EDITOR .env
docker compose --env-file .env config --quiet
docker compose --env-file .env up --build
```

Open:

- Dashboard: http://localhost:3000
- Backend API docs: http://localhost:8000/docs

The self-hosted compose file builds local images from this repository. It does not pull Airflow Observer images from GHCR or Docker Hub.

## Required Configuration

`DEMO_MODE=false` is the default for self-hosted deployments. In that mode, the backend refuses to start unless the required settings are present.

Minimum values to replace in `.env`:

| Variable | Used by | Description |
| --- | --- | --- |
| `POSTGRES_PASSWORD` | Postgres/backend | Strong database password. |
| `DATABASE_URL` | backend | SQLAlchemy URL for the Observer Postgres database. |
| `DEFAULT_WORKSPACE_ID` | backend | Workspace id created at startup. |
| `DEFAULT_API_KEY` | backend | API key accepted by protected endpoints. |
| `CORS_ORIGINS` | backend | Comma-separated browser origins allowed by the backend. |
| `AIRFLOW_URL` | agent | Base URL of your Airflow webserver/API. |
| `AIRFLOW_USERNAME` / `AIRFLOW_PASSWORD` | agent | Basic auth credentials when not using token auth. |
| `AIRFLOW_TOKEN` | agent | Bearer token. Takes precedence over Basic auth. |
| `OBSERVER_API_KEY` | agent | Must match backend `DEFAULT_API_KEY`. |
| `WORKSPACE_ID` | agent | Must match backend `DEFAULT_WORKSPACE_ID`. |
| `AIRFLOW_INSTANCE_UID` | agent | Stable id for this Airflow instance. |
| `AIRFLOW_INSTANCE_NAME` | agent | Human-readable Airflow instance name. |

Optional values:

| Variable | Description |
| --- | --- |
| `SLACK_WEBHOOK_URL` | Optional default Slack webhook for test alerts. |
| `POLL_INTERVAL_SECONDS` | Agent polling interval. Defaults to `60`. |
| `DAG_FILTER_REGEX` | Regex to limit collected DAGs. Defaults to `.*`. |
| `DAG_LIMIT` | Max DAGs fetched per poll. Defaults to `100`. |
| `RUN_LIMIT` | Max runs fetched per DAG. Defaults to `10`. |

## API

Read endpoints:

```text
GET /health
GET /api/v1/overview
GET /api/v1/dags
GET /api/v1/dags/{dag_id}
GET /api/v1/incidents
GET /api/v1/recommendations
GET /api/v1/agent/status
GET /api/v1/onboarding
GET /api/v1/alert-channels
```

Protected endpoints:

```text
POST /api/v1/ingest/snapshot
POST /api/v1/alert-channels
POST /api/v1/alert-channels/{channel_id}/test
POST /api/v1/alerts/slack/test
```

Protected requests require:

```text
X-API-Key: <your-observer-api-key>
```

## Slack Alerts

Create a Slack channel through the API so webhook URLs stay out of the browser:

```powershell
curl -X POST http://localhost:8000/api/v1/alert-channels `
  -H "Content-Type: application/json" `
  -H "X-API-Key: <your-observer-api-key>" `
  -d "{\"kind\":\"slack\",\"name\":\"Data alerts\",\"target\":\"https://hooks.slack.com/services/...\",\"is_enabled\":true}"
```

Test a channel:

```powershell
curl -X POST http://localhost:8000/api/v1/alert-channels/1/test `
  -H "X-API-Key: <your-observer-api-key>"
```

## Operations

- Rotate the Observer API key by updating backend `DEFAULT_API_KEY`, agent `OBSERVER_API_KEY`, and restarting both services.
- Back up the Postgres database or Docker volume with your normal Postgres backup process.
- Put HTTPS and authentication controls in front of exposed services.
- Restrict backend network access to trusted agents and the dashboard.
- Keep `.env`, Slack webhooks, Airflow tokens, and database backups out of Git.
- Check runtime status with `docker compose ps`.
- Inspect logs with `docker compose logs -f backend agent frontend`.

## Development

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
pytest
```

Agent:

```powershell
cd agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest
```

Frontend:

```powershell
cd frontend
corepack enable
pnpm install
pnpm dev
pnpm build
```

Docker configuration checks:

```powershell
docker compose --env-file .env.example config --quiet
docker compose --env-file .env.demo -f docker-compose.yml -f docker-compose.demo.yml config --quiet
```

## Current Limits

Airflow Observer is not a full SaaS platform. It currently does not include:

- built-in user login;
- SSO;
- advanced RBAC;
- billing;
- hosted image publishing;
- Kubernetes manifests;
- Terraform;
- full task log ingestion;
- lineage;
- data quality checks.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

See [SECURITY.md](SECURITY.md).

## License

MIT. See [LICENSE](LICENSE).
