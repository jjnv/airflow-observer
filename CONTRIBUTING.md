# Contributing

Thanks for helping improve Airflow Observer.

## Local checks

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
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
pnpm build
```

Docker configuration:

```powershell
docker compose --env-file .env.example config --quiet
docker compose --env-file .env.demo -f docker-compose.yml -f docker-compose.demo.yml config --quiet
```

## Pull requests

- Keep changes focused and include tests for behavior changes.
- Do not commit real credentials, webhook URLs, database dumps, or Airflow logs.
- Update `README.md` when setup, configuration, or public API behavior changes.
- Prefer small, operationally clear changes over broad rewrites.
