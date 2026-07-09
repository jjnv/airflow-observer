from airflow_observer_agent.airflow_client import AirflowClient
from airflow_observer_agent.config import AgentConfig


def config(**overrides):
    values = {
        "airflow_url": "http://airflow:8080",
        "airflow_username": None,
        "airflow_password": None,
        "airflow_token": None,
        "observer_api_url": "http://backend:8000",
        "observer_api_key": "key",
        "workspace_id": "demo-workspace",
        "airflow_instance_uid": "local-airflow",
        "airflow_instance_name": "Local Airflow",
        "agent_version": "0.1.0",
        "poll_interval_seconds": 60,
        "dag_limit": 100,
        "run_limit": 10,
        "dag_filter_regex": None,
    }
    values.update(overrides)
    return AgentConfig(**values)


def test_airflow_client_uses_bearer_token_when_present():
    client = AirflowClient(config(airflow_token="token", airflow_username="admin", airflow_password="admin"))

    assert client.session.headers["Authorization"] == "Bearer token"
    assert client.session.auth is None


def test_airflow_client_uses_basic_auth_without_token():
    client = AirflowClient(config(airflow_username="admin", airflow_password="secret"))

    assert client.session.auth == ("admin", "secret")
