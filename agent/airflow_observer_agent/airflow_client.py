from datetime import datetime
from urllib.parse import quote

import requests

from airflow_observer_agent.config import AgentConfig


class AirflowClient:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.session = requests.Session()
        if config.airflow_token:
            self.session.headers.update({"Authorization": f"Bearer {config.airflow_token}"})
        elif config.airflow_username and config.airflow_password:
            self.session.auth = (config.airflow_username, config.airflow_password)

    def _get(self, path: str, params: dict | None = None) -> dict:
        response = self.session.get(f"{self.config.airflow_url}{path}", params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def list_dags(self) -> list[dict]:
        payload = self._get("/api/v1/dags", {"limit": self.config.dag_limit})
        return payload.get("dags", [])

    def list_dag_runs(self, dag_id: str) -> list[dict]:
        encoded_dag_id = quote(dag_id, safe="")
        payload = self._get(
            f"/api/v1/dags/{encoded_dag_id}/dagRuns",
            {"limit": self.config.run_limit, "order_by": "-start_date"},
        )
        return payload.get("dag_runs", [])

    def list_task_instances(self, dag_id: str, run_id: str) -> list[dict]:
        encoded_dag_id = quote(dag_id, safe="")
        encoded_run_id = quote(run_id, safe="")
        payload = self._get(f"/api/v1/dags/{encoded_dag_id}/dagRuns/{encoded_run_id}/taskInstances")
        return payload.get("task_instances", [])


def parse_airflow_datetime(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return value


def duration_seconds(start: str | None, end: str | None, explicit: float | None = None) -> float | None:
    if explicit is not None:
        return explicit
    if not start or not end:
        return None
    try:
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
    except ValueError:
        return None
    return max((end_dt - start_dt).total_seconds(), 0.0)
