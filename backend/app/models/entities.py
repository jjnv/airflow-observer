from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    key: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, default="default")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    workspace: Mapped[Workspace] = relationship(back_populates="api_keys")


class AirflowInstance(Base):
    __tablename__ = "airflow_instances"
    __table_args__ = (UniqueConstraint("workspace_id", "external_id", name="uq_airflow_instance_external"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    external_id: Mapped[str] = mapped_column(String(160), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    agent_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_snapshot_dag_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_snapshot_dag_run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_snapshot_task_run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Dag(Base):
    __tablename__ = "dags"
    __table_args__ = (UniqueConstraint("workspace_id", "dag_id", name="uq_dag_workspace_dag_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    airflow_instance_id: Mapped[int] = mapped_column(ForeignKey("airflow_instances.id", ondelete="CASCADE"))
    dag_id: Mapped[str] = mapped_column(String(250), nullable=False, index=True)
    owner: Mapped[str | None] = mapped_column(String(250), nullable=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    runs: Mapped[list["DagRun"]] = relationship(back_populates="dag", cascade="all, delete-orphan")
    tasks: Mapped[list["Task"]] = relationship(back_populates="dag", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (UniqueConstraint("dag_id_fk", "task_id", name="uq_task_dag_task_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dag_id_fk: Mapped[int] = mapped_column(ForeignKey("dags.id", ondelete="CASCADE"), index=True)
    task_id: Mapped[str] = mapped_column(String(250), nullable=False)
    operator: Mapped[str | None] = mapped_column(String(250), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(250), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    dag: Mapped[Dag] = relationship(back_populates="tasks")


class DagRun(Base):
    __tablename__ = "dag_runs"
    __table_args__ = (UniqueConstraint("workspace_id", "dag_id_fk", "run_id", name="uq_dag_run"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    dag_id_fk: Mapped[int] = mapped_column(ForeignKey("dags.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[str] = mapped_column(String(320), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    dag: Mapped[Dag] = relationship(back_populates="runs")
    task_runs: Mapped[list["TaskRun"]] = relationship(back_populates="dag_run", cascade="all, delete-orphan")


class TaskRun(Base):
    __tablename__ = "task_runs"
    __table_args__ = (UniqueConstraint("dag_run_id", "task_id", "try_number", name="uq_task_run"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dag_run_id: Mapped[int] = mapped_column(ForeignKey("dag_runs.id", ondelete="CASCADE"), index=True)
    task_id: Mapped[str] = mapped_column(String(250), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")
    try_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    dag_run: Mapped[DagRun] = relationship(back_populates="task_runs")


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    dag_id: Mapped[str] = mapped_column(String(250), nullable=False, index=True)
    task_id: Mapped[str | None] = mapped_column(String(250), nullable=True)
    title: Mapped[str] = mapped_column(String(320), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open")
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    dag_id: Mapped[str] = mapped_column(String(250), nullable=False, index=True)
    task_id: Mapped[str | None] = mapped_column(String(250), nullable=True)
    kind: Mapped[str] = mapped_column(String(80), nullable=False, default="generic")
    title: Mapped[str] = mapped_column(String(320), nullable=False)
    impact: Mapped[str] = mapped_column(String(50), nullable=False, default="medium")
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    estimated_savings_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AlertChannel(Base):
    __tablename__ = "alert_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(50), nullable=False, default="slack")
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    target: Mapped[str] = mapped_column(Text, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
