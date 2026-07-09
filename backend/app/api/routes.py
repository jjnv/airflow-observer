from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.entities import AirflowInstance, AlertChannel, ApiKey, Dag, DagRun, Incident, Recommendation
from app.schemas.alerts import AlertChannelIn
from app.schemas.ingest import SnapshotIn
from app.services.analytics import get_overview, recompute_workspace_analytics
from app.services.ingest import ingest_snapshot
from app.services.slack import post_slack_message

router = APIRouter(prefix="/api/v1")


def require_api_key(
    x_api_key: str = Header(alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> ApiKey:
    api_key = db.query(ApiKey).filter(ApiKey.key == x_api_key).one_or_none()
    if api_key is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


@router.post("/ingest/snapshot")
def ingest_airflow_snapshot(
    snapshot: SnapshotIn,
    api_key: ApiKey = Depends(require_api_key),
    db: Session = Depends(get_db),
):
    if snapshot.workspace_id != api_key.workspace_id:
        raise HTTPException(status_code=403, detail="API key does not belong to workspace")
    counts = ingest_snapshot(db, snapshot)
    recompute_workspace_analytics(db, snapshot.workspace_id)
    return {"ok": True, "ingested": counts}


@router.get("/overview")
def overview(
    workspace_id: str = Query(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return get_overview(db, workspace_id or settings.default_workspace_id)


@router.get("/agent/status")
def agent_status(
    workspace_id: str = Query(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    target_workspace = workspace_id or settings.default_workspace_id
    agents = (
        db.query(AirflowInstance)
        .filter(AirflowInstance.workspace_id == target_workspace, AirflowInstance.agent_version.isnot(None))
        .order_by(desc(AirflowInstance.last_heartbeat_at))
        .all()
    )
    return {"agents": [_agent_payload(agent) for agent in agents]}


@router.get("/onboarding")
def onboarding(
    workspace_id: str = Query(default=None),
    settings: Settings = Depends(get_settings),
):
    target_workspace = workspace_id or settings.default_workspace_id
    return {
        "workspace_id": target_workspace,
        "api_key_env_var": "OBSERVER_API_KEY",
        "steps": [
            "Create or select a workspace.",
            "Generate a strong Observer API key and set DEFAULT_API_KEY on the backend.",
            "Run the Docker agent near your Airflow instance.",
            "Wait for the first snapshot and confirm the agent appears online.",
        ],
        "docker_command": (
            "docker build -t airflow-observer-agent ./agent && "
            "docker run --rm --env-file .env airflow-observer-agent --once"
        ),
        "docker_compose_service": {
            "build": "./agent",
            "environment": {
                "AIRFLOW_URL": "https://airflow.company.com",
                "AIRFLOW_USERNAME": "${AIRFLOW_USERNAME}",
                "AIRFLOW_PASSWORD": "${AIRFLOW_PASSWORD}",
                "AIRFLOW_TOKEN": "${AIRFLOW_TOKEN}",
                "OBSERVER_API_URL": "https://observer.example.com",
                "OBSERVER_API_KEY": "${OBSERVER_API_KEY}",
                "WORKSPACE_ID": target_workspace,
                "POLL_INTERVAL_SECONDS": "60",
                "DAG_FILTER_REGEX": ".*",
            },
        },
    }


@router.get("/dags")
def list_dags(
    workspace_id: str = Query(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    target_workspace = workspace_id or settings.default_workspace_id
    dags = db.query(Dag).filter(Dag.workspace_id == target_workspace).order_by(Dag.dag_id).all()
    result = []
    for dag in dags:
        latest = (
            db.query(DagRun)
            .filter(DagRun.dag_id_fk == dag.id)
            .order_by(desc(DagRun.execution_date), desc(DagRun.id))
            .first()
        )
        result.append(
            {
                "dag_id": dag.dag_id,
                "owner": dag.owner,
                "tags": dag.tags,
                "is_active": dag.is_active,
                "is_paused": dag.is_paused,
                "latest_state": latest.state if latest else "unknown",
                "latest_duration_seconds": latest.duration_seconds if latest else None,
                "latest_run_id": latest.run_id if latest else None,
            }
        )
    return {"dags": result}


@router.get("/dags/{dag_id}")
def dag_detail(
    dag_id: str,
    workspace_id: str = Query(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    target_workspace = workspace_id or settings.default_workspace_id
    dag = db.query(Dag).filter(Dag.workspace_id == target_workspace, Dag.dag_id == dag_id).one_or_none()
    if dag is None:
        raise HTTPException(status_code=404, detail="DAG not found")

    runs = (
        db.query(DagRun)
        .options(joinedload(DagRun.task_runs))
        .filter(DagRun.dag_id_fk == dag.id)
        .order_by(desc(DagRun.execution_date), desc(DagRun.id))
        .limit(50)
        .all()
    )
    recommendations = (
        db.query(Recommendation)
        .filter(
            Recommendation.workspace_id == target_workspace,
            Recommendation.dag_id == dag_id,
            Recommendation.status == "active",
        )
        .order_by(desc(Recommendation.score))
        .all()
    )
    incidents = (
        db.query(Incident)
        .filter(Incident.workspace_id == target_workspace, Incident.dag_id == dag_id, Incident.status == "open")
        .order_by(desc(Incident.last_seen_at))
        .all()
    )
    return {
        "dag": {
            "dag_id": dag.dag_id,
            "owner": dag.owner,
            "tags": dag.tags,
            "is_active": dag.is_active,
            "is_paused": dag.is_paused,
        },
        "runs": [
            {
                "run_id": run.run_id,
                "state": run.state,
                "start_time": run.start_time,
                "end_time": run.end_time,
                "execution_date": run.execution_date,
                "duration_seconds": run.duration_seconds,
                "tasks": [
                    {
                        "task_id": task.task_id,
                        "state": task.state,
                        "try_number": task.try_number,
                        "duration_seconds": task.duration_seconds,
                        "error_summary": task.error_summary,
                    }
                    for task in sorted(run.task_runs, key=lambda item: item.duration_seconds or 0, reverse=True)
                ],
            }
            for run in runs
        ],
        "incidents": [
            {
                "title": item.title,
                "task_id": item.task_id,
                "severity": item.severity,
                "error_summary": item.error_summary,
                "consecutive_failures": item.consecutive_failures,
                "last_seen_at": item.last_seen_at,
            }
            for item in incidents
        ],
        "recommendations": [
            _recommendation_payload(item)
            for item in recommendations
        ],
    }


@router.get("/incidents")
def list_incidents(
    workspace_id: str = Query(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    target_workspace = workspace_id or settings.default_workspace_id
    incidents = (
        db.query(Incident)
        .filter(Incident.workspace_id == target_workspace, Incident.status == "open")
        .order_by(desc(Incident.severity), desc(Incident.last_seen_at))
        .all()
    )
    return {
        "incidents": [
            {
                "id": item.id,
                "dag_id": item.dag_id,
                "task_id": item.task_id,
                "title": item.title,
                "severity": item.severity,
                "status": item.status,
                "error_summary": item.error_summary,
                "consecutive_failures": item.consecutive_failures,
                "last_seen_at": item.last_seen_at,
            }
            for item in incidents
        ]
    }


@router.get("/recommendations")
def list_recommendations(
    workspace_id: str = Query(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    target_workspace = workspace_id or settings.default_workspace_id
    recommendations = (
        db.query(Recommendation)
        .filter(Recommendation.workspace_id == target_workspace, Recommendation.status == "active")
        .order_by(desc(Recommendation.score))
        .all()
    )
    return {
        "recommendations": [
            _recommendation_payload(item)
            for item in recommendations
        ]
    }


@router.get("/alert-channels")
def list_alert_channels(
    workspace_id: str = Query(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    target_workspace = workspace_id or settings.default_workspace_id
    channels = db.query(AlertChannel).filter(AlertChannel.workspace_id == target_workspace).order_by(AlertChannel.id).all()
    return {"channels": [_alert_channel_payload(channel) for channel in channels]}


@router.post("/alert-channels")
def create_alert_channel(
    payload: AlertChannelIn,
    api_key: ApiKey = Depends(require_api_key),
    db: Session = Depends(get_db),
):
    channel = AlertChannel(
        workspace_id=api_key.workspace_id,
        kind=payload.kind,
        name=payload.name,
        target=payload.target,
        is_enabled=payload.is_enabled,
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return _alert_channel_payload(channel)


@router.post("/alert-channels/{channel_id}/test")
def test_alert_channel(
    channel_id: int,
    api_key: ApiKey = Depends(require_api_key),
    db: Session = Depends(get_db),
):
    channel = (
        db.query(AlertChannel)
        .filter(AlertChannel.id == channel_id, AlertChannel.workspace_id == api_key.workspace_id)
        .one_or_none()
    )
    if channel is None:
        raise HTTPException(status_code=404, detail="Alert channel not found")
    if not channel.is_enabled:
        raise HTTPException(status_code=400, detail="Alert channel is disabled")
    post_slack_message(channel.target, f"Airflow Observer test alert for channel {channel.name}.")
    return {"ok": True}


@router.post("/alerts/slack/test")
def test_slack_alert(
    api_key: ApiKey = Depends(require_api_key),
    settings: Settings = Depends(get_settings),
):
    if not settings.slack_webhook_url:
        raise HTTPException(status_code=400, detail="SLACK_WEBHOOK_URL is not configured")
    post_slack_message(
        settings.slack_webhook_url,
        f"Airflow Observer test alert for workspace {api_key.workspace_id}.",
    )
    return {"ok": True}


def _recommendation_payload(item: Recommendation) -> dict:
    return {
        "id": item.id,
        "dag_id": item.dag_id,
        "task_id": item.task_id,
        "kind": item.kind,
        "title": item.title,
        "impact": item.impact,
        "reason": item.reason,
        "evidence_count": item.evidence_count,
        "estimated_savings_seconds": item.estimated_savings_seconds,
        "score": item.score,
        "status": item.status,
    }


def _agent_payload(agent: AirflowInstance) -> dict:
    last_seen = agent.last_heartbeat_at
    seconds_since_seen = None
    status = "never_seen"
    if last_seen:
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=UTC)
        seconds_since_seen = max((datetime.now(UTC) - last_seen).total_seconds(), 0)
        status = "online" if seconds_since_seen <= 180 else "stale"
    return {
        "airflow_instance_uid": agent.external_id,
        "name": agent.name,
        "base_url": agent.base_url,
        "agent_version": agent.agent_version,
        "last_heartbeat_at": agent.last_heartbeat_at,
        "seconds_since_seen": seconds_since_seen,
        "status": status,
        "last_snapshot": {
            "dags": agent.last_snapshot_dag_count,
            "dag_runs": agent.last_snapshot_dag_run_count,
            "task_runs": agent.last_snapshot_task_run_count,
        },
    }


def _alert_channel_payload(channel: AlertChannel) -> dict:
    return {
        "id": channel.id,
        "workspace_id": channel.workspace_id,
        "kind": channel.kind,
        "name": channel.name,
        "is_enabled": channel.is_enabled,
        "target_preview": channel.target[:32] + "..." if len(channel.target) > 32 else channel.target,
        "created_at": channel.created_at,
    }
