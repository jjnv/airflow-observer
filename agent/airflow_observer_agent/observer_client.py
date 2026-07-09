import time

import requests

from airflow_observer_agent.config import AgentConfig


class ObserverClient:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": config.observer_api_key})

    def post_snapshot(self, snapshot: dict, attempts: int = 3) -> dict:
        url = f"{self.config.observer_api_url}/api/v1/ingest/snapshot"
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                response = self.session.post(url, json=snapshot, timeout=30)
                response.raise_for_status()
                return response.json()
            except requests.RequestException as exc:
                last_error = exc
                if attempt < attempts:
                    time.sleep(min(attempt * 2, 10))
        raise RuntimeError(f"Could not post snapshot to Observer API: {last_error}") from last_error
