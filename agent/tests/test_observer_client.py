import requests

from airflow_observer_agent.config import AgentConfig
from airflow_observer_agent.observer_client import ObserverClient


class FakeResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError("boom")

    def json(self):
        return {"ok": True}


def config():
    return AgentConfig(
        airflow_url="http://airflow:8080",
        airflow_username=None,
        airflow_password=None,
        airflow_token=None,
        observer_api_url="http://backend:8000",
        observer_api_key="key",
        workspace_id="demo-workspace",
        airflow_instance_uid="local-airflow",
        airflow_instance_name="Local Airflow",
        agent_version="0.1.0",
        poll_interval_seconds=60,
        dag_limit=100,
        run_limit=10,
        dag_filter_regex=None,
    )


def test_post_snapshot_retries_once(monkeypatch):
    client = ObserverClient(config())
    calls = {"count": 0}

    def fake_post(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise requests.ConnectionError("temporary")
        return FakeResponse()

    monkeypatch.setattr(client.session, "post", fake_post)
    monkeypatch.setattr("time.sleep", lambda _: None)

    assert client.post_snapshot({"dags": []}) == {"ok": True}
    assert calls["count"] == 2
