from airflow_observer_agent.config import AgentConfig
from airflow_observer_agent.snapshot import build_snapshot


class FakeAirflowClient:
    def list_dags(self):
        return [
            {
                "dag_id": "orders_etl",
                "owners": ["data"],
                "tags": [{"name": "warehouse"}],
                "is_active": True,
                "is_paused": False,
            },
            {
                "dag_id": "skip_me",
                "owners": ["data"],
                "tags": [],
                "is_active": True,
                "is_paused": False,
            },
        ]

    def list_dag_runs(self, dag_id):
        if dag_id == "skip_me":
            return []
        assert dag_id == "orders_etl"
        return [
            {
                "dag_run_id": "manual__1",
                "state": "success",
                "start_date": "2026-07-09T08:00:00+00:00",
                "end_date": "2026-07-09T08:10:00+00:00",
                "logical_date": "2026-07-09T08:00:00+00:00",
            }
        ]

    def list_task_instances(self, dag_id, run_id):
        assert dag_id == "orders_etl"
        assert run_id == "manual__1"
        return [
            {
                "task_id": "load",
                "state": "success",
                "try_number": 1,
                "start_date": "2026-07-09T08:02:00+00:00",
                "end_date": "2026-07-09T08:10:00+00:00",
                "operator": "PythonOperator",
            }
        ]


def test_build_snapshot_normalizes_airflow_payload():
    config = AgentConfig(
        airflow_url="http://airflow:8080",
        airflow_username="admin",
        airflow_password="admin",
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

    snapshot = build_snapshot(config, FakeAirflowClient())

    assert snapshot["workspace_id"] == "demo-workspace"
    assert snapshot["agent_version"] == "0.1.0"
    assert snapshot["dags"][0]["dag_id"] == "orders_etl"
    assert snapshot["dags"][0]["owner"] == "data"
    assert snapshot["dags"][0]["tags"] == ["warehouse"]
    assert snapshot["dags"][0]["runs"][0]["duration_seconds"] == 600
    assert snapshot["dags"][0]["runs"][0]["tasks"][0]["duration_seconds"] == 480


def test_build_snapshot_applies_dag_filter_regex():
    config = AgentConfig(
        airflow_url="http://airflow:8080",
        airflow_username="admin",
        airflow_password="admin",
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
        dag_filter_regex="^orders_",
    )

    snapshot = build_snapshot(config, FakeAirflowClient())

    assert [dag["dag_id"] for dag in snapshot["dags"]] == ["orders_etl"]
