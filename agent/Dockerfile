FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY airflow_observer_agent ./airflow_observer_agent

HEALTHCHECK --interval=60s --timeout=5s --start-period=90s --retries=3 CMD python -c "from pathlib import Path; import time; p=Path('/tmp/airflow-observer-agent-heartbeat'); raise SystemExit(0 if p.exists() and time.time() - float(p.read_text()) < 240 else 1)"

ENTRYPOINT ["python", "-m", "airflow_observer_agent.cli"]
