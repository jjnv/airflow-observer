from datetime import UTC, datetime
import re

from airflow_observer_agent.airflow_client import AirflowClient, duration_seconds, parse_airflow_datetime
from airflow_observer_agent.config import AgentConfig


def build_snapshot(config: AgentConfig, client: AirflowClient) -> dict:
    dags = []
    dag_filter = re.compile(config.dag_filter_regex) if config.dag_filter_regex else None
    for dag in client.list_dags():
        dag_id = dag["dag_id"]
        if dag_filter and not dag_filter.search(dag_id):
            continue
        runs = []
        for run in client.list_dag_runs(dag_id):
            run_id = run["dag_run_id"]
            tasks = []
            for task in client.list_task_instances(dag_id, run_id):
                start = parse_airflow_datetime(task.get("start_date"))
                end = parse_airflow_datetime(task.get("end_date"))
                state = task.get("state") or "unknown"
                tasks.append(
                    {
                        "task_id": task["task_id"],
                        "state": state,
                        "try_number": task.get("try_number") or 1,
                        "start_time": start,
                        "end_time": end,
                        "duration_seconds": duration_seconds(start, end, task.get("duration")),
                        "error_summary": _error_summary(task) if state in {"failed", "upstream_failed"} else None,
                        "operator": task.get("operator"),
                        "owner": task.get("owner"),
                    }
                )
            start = parse_airflow_datetime(run.get("start_date"))
            end = parse_airflow_datetime(run.get("end_date"))
            runs.append(
                {
                    "run_id": run_id,
                    "state": run.get("state") or "unknown",
                    "start_time": start,
                    "end_time": end,
                    "execution_date": parse_airflow_datetime(run.get("execution_date") or run.get("logical_date")),
                    "duration_seconds": duration_seconds(start, end),
                    "tasks": tasks,
                }
            )
        dags.append(
            {
                "dag_id": dag_id,
                "owner": _owner_from_dag(dag),
                "tags": _tags_from_dag(dag),
                "is_active": bool(dag.get("is_active", True)),
                "is_paused": bool(dag.get("is_paused", False)),
                "runs": runs,
            }
        )
    return {
        "workspace_id": config.workspace_id,
        "airflow_instance_uid": config.airflow_instance_uid,
        "airflow_instance_name": config.airflow_instance_name,
        "airflow_base_url": config.airflow_url,
        "agent_version": config.agent_version,
        "collected_at": datetime.now(UTC).isoformat(),
        "dags": dags,
    }


def _owner_from_dag(dag: dict) -> str | None:
    owners = dag.get("owners")
    if isinstance(owners, list) and owners:
        return ",".join(str(owner) for owner in owners)
    return dag.get("owner")


def _tags_from_dag(dag: dict) -> list[str]:
    tags = dag.get("tags") or []
    normalized = []
    for tag in tags:
        if isinstance(tag, dict) and tag.get("name"):
            normalized.append(str(tag["name"]))
        elif isinstance(tag, str):
            normalized.append(tag)
    return normalized


def _error_summary(task: dict) -> str:
    note = task.get("note")
    if note:
        return str(note)[:500]
    return "Task failed in Airflow. Inspect task logs in the Airflow UI for the full traceback."
