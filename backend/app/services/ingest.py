import json
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.entities import AirflowInstance, Dag, DagRun, Task, TaskRun
from app.schemas.ingest import SnapshotIn


def _now() -> datetime:
    return datetime.now(UTC)


def _duration(start: datetime | None, end: datetime | None, explicit: float | None) -> float | None:
    if explicit is not None:
        return explicit
    if start and end:
        return max((end - start).total_seconds(), 0.0)
    return None


def ingest_snapshot(db: Session, snapshot: SnapshotIn) -> dict[str, int]:
    airflow_instance = (
        db.query(AirflowInstance)
        .filter(
            AirflowInstance.workspace_id == snapshot.workspace_id,
            AirflowInstance.external_id == snapshot.airflow_instance_uid,
        )
        .one_or_none()
    )
    if airflow_instance is None:
        airflow_instance = AirflowInstance(
            workspace_id=snapshot.workspace_id,
            external_id=snapshot.airflow_instance_uid,
            name=snapshot.airflow_instance_name,
            base_url=snapshot.airflow_base_url,
        )
        db.add(airflow_instance)
        db.flush()
    else:
        airflow_instance.name = snapshot.airflow_instance_name
        airflow_instance.base_url = snapshot.airflow_base_url
    airflow_instance.agent_version = snapshot.agent_version
    airflow_instance.last_heartbeat_at = snapshot.collected_at or _now()
    airflow_instance.updated_at = _now()

    counts = {"dags": 0, "dag_runs": 0, "task_runs": 0}

    for dag_in in snapshot.dags:
        dag = (
            db.query(Dag)
            .filter(Dag.workspace_id == snapshot.workspace_id, Dag.dag_id == dag_in.dag_id)
            .one_or_none()
        )
        if dag is None:
            dag = Dag(
                workspace_id=snapshot.workspace_id,
                airflow_instance_id=airflow_instance.id,
                dag_id=dag_in.dag_id,
            )
            db.add(dag)
            db.flush()
        dag.airflow_instance_id = airflow_instance.id
        dag.owner = dag_in.owner
        dag.tags = json.dumps(dag_in.tags)
        dag.is_active = dag_in.is_active
        dag.is_paused = dag_in.is_paused
        dag.last_seen_at = snapshot.collected_at or _now()
        counts["dags"] += 1

        for run_in in dag_in.runs:
            dag_run = (
                db.query(DagRun)
                .filter(
                    DagRun.workspace_id == snapshot.workspace_id,
                    DagRun.dag_id_fk == dag.id,
                    DagRun.run_id == run_in.run_id,
                )
                .one_or_none()
            )
            if dag_run is None:
                dag_run = DagRun(workspace_id=snapshot.workspace_id, dag_id_fk=dag.id, run_id=run_in.run_id)
                db.add(dag_run)
                db.flush()
            dag_run.state = run_in.state
            dag_run.start_time = run_in.start_time
            dag_run.end_time = run_in.end_time
            dag_run.execution_date = run_in.execution_date
            dag_run.duration_seconds = _duration(run_in.start_time, run_in.end_time, run_in.duration_seconds)
            counts["dag_runs"] += 1

            for task_in in run_in.tasks:
                task = db.query(Task).filter(Task.dag_id_fk == dag.id, Task.task_id == task_in.task_id).one_or_none()
                if task is None:
                    task = Task(dag_id_fk=dag.id, task_id=task_in.task_id)
                    db.add(task)
                task.operator = task_in.operator
                task.owner = task_in.owner
                task.last_seen_at = snapshot.collected_at or _now()

                task_run = (
                    db.query(TaskRun)
                    .filter(
                        TaskRun.dag_run_id == dag_run.id,
                        TaskRun.task_id == task_in.task_id,
                        TaskRun.try_number == task_in.try_number,
                    )
                    .one_or_none()
                )
                if task_run is None:
                    task_run = TaskRun(
                        dag_run_id=dag_run.id,
                        task_id=task_in.task_id,
                        try_number=task_in.try_number,
                    )
                    db.add(task_run)
                task_run.state = task_in.state
                task_run.start_time = task_in.start_time
                task_run.end_time = task_in.end_time
                task_run.duration_seconds = _duration(task_in.start_time, task_in.end_time, task_in.duration_seconds)
                task_run.error_summary = task_in.error_summary
                counts["task_runs"] += 1

    airflow_instance.last_snapshot_dag_count = counts["dags"]
    airflow_instance.last_snapshot_dag_run_count = counts["dag_runs"]
    airflow_instance.last_snapshot_task_run_count = counts["task_runs"]
    db.commit()
    return counts
