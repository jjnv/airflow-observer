from dataclasses import dataclass
import os


@dataclass(frozen=True)
class AgentConfig:
    airflow_url: str
    airflow_username: str | None
    airflow_password: str | None
    airflow_token: str | None
    observer_api_url: str
    observer_api_key: str
    workspace_id: str
    airflow_instance_uid: str
    airflow_instance_name: str
    agent_version: str
    poll_interval_seconds: int
    dag_limit: int
    run_limit: int
    dag_filter_regex: str | None

    @classmethod
    def from_env(cls) -> "AgentConfig":
        return cls(
            airflow_url=_required_env("AIRFLOW_URL").rstrip("/"),
            airflow_username=os.getenv("AIRFLOW_USERNAME"),
            airflow_password=os.getenv("AIRFLOW_PASSWORD"),
            airflow_token=os.getenv("AIRFLOW_TOKEN"),
            observer_api_url=os.getenv("OBSERVER_API_URL", "http://backend:8000").rstrip("/"),
            observer_api_key=_required_env("OBSERVER_API_KEY"),
            workspace_id=_required_env("WORKSPACE_ID"),
            airflow_instance_uid=_required_env("AIRFLOW_INSTANCE_UID"),
            airflow_instance_name=_required_env("AIRFLOW_INSTANCE_NAME"),
            agent_version=os.getenv("AGENT_VERSION", "0.1.0"),
            poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "60")),
            dag_limit=int(os.getenv("DAG_LIMIT", "100")),
            run_limit=int(os.getenv("RUN_LIMIT", "10")),
            dag_filter_regex=os.getenv("DAG_FILTER_REGEX"),
        )


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} must be set.")
    return value
