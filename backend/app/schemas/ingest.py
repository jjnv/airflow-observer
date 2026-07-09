from datetime import datetime

from pydantic import BaseModel, Field


class TaskRunIn(BaseModel):
    task_id: str
    state: str = "unknown"
    try_number: int = 1
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_seconds: float | None = None
    error_summary: str | None = None
    operator: str | None = None
    owner: str | None = None


class DagRunIn(BaseModel):
    run_id: str
    state: str = "unknown"
    start_time: datetime | None = None
    end_time: datetime | None = None
    execution_date: datetime | None = None
    duration_seconds: float | None = None
    tasks: list[TaskRunIn] = Field(default_factory=list)


class DagIn(BaseModel):
    dag_id: str
    owner: str | None = None
    tags: list[str] = Field(default_factory=list)
    is_active: bool = True
    is_paused: bool = False
    runs: list[DagRunIn] = Field(default_factory=list)


class SnapshotIn(BaseModel):
    workspace_id: str
    airflow_instance_uid: str = "default"
    airflow_instance_name: str = "Default Airflow"
    airflow_base_url: str | None = None
    agent_version: str | None = None
    collected_at: datetime | None = None
    dags: list[DagIn] = Field(default_factory=list)
