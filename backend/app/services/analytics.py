from collections import defaultdict
from statistics import median

from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, func
from sqlalchemy.orm import Session, joinedload

from app.models.entities import AirflowInstance, Dag, DagRun, Incident, Recommendation, TaskRun


SUCCESS_STATES = {"success"}
FAILURE_STATES = {"failed", "upstream_failed"}


def percentile(values: list[float], percent: float) -> float | None:
    if not values:
        return None
    sorted_values = sorted(values)
    index = round((len(sorted_values) - 1) * percent)
    return sorted_values[index]


def recompute_workspace_analytics(db: Session, workspace_id: str) -> None:
    active_incidents: set[tuple[str, str | None, str]] = set()
    active_recommendations: set[tuple[str, str | None, str]] = set()

    dags = db.query(Dag).filter(Dag.workspace_id == workspace_id).all()
    for dag in dags:
        runs = (
            db.query(DagRun)
            .options(joinedload(DagRun.task_runs))
            .filter(DagRun.workspace_id == workspace_id, DagRun.dag_id_fk == dag.id)
            .order_by(desc(DagRun.execution_date), desc(DagRun.start_time), desc(DagRun.id))
            .limit(25)
            .all()
        )
        active_incidents.update(_create_failure_incidents(db, workspace_id, dag.dag_id, runs))
        active_recommendations.update(_create_duration_recommendations(db, workspace_id, dag.dag_id, runs))
        active_recommendations.update(_create_metadata_recommendations(db, workspace_id, dag))

    _resolve_stale_incidents(db, workspace_id, active_incidents)
    _resolve_stale_recommendations(db, workspace_id, active_recommendations)

    db.commit()


def _create_failure_incidents(db: Session, workspace_id: str, dag_id: str, runs: list[DagRun]) -> set[tuple[str, str | None, str]]:
    active: set[tuple[str, str | None, str]] = set()
    consecutive_dag_failures = 0
    for run in runs:
        if run.state in FAILURE_STATES:
            consecutive_dag_failures += 1
        else:
            break

    if consecutive_dag_failures >= 2:
        last = runs[0]
        title = f"{dag_id} failed {consecutive_dag_failures} runs in a row"
        _upsert_incident(
            db,
            workspace_id=workspace_id,
            dag_id=dag_id,
            task_id=None,
            title=title,
            severity="high",
            error_summary="DAG has repeated failed runs.",
            consecutive_failures=consecutive_dag_failures,
            first_seen_at=runs[consecutive_dag_failures - 1].start_time or runs[consecutive_dag_failures - 1].created_at,
            last_seen_at=last.end_time or last.start_time or last.created_at,
        )
        active.add((dag_id, None, title))

    failures_by_task: dict[str, list[TaskRun]] = defaultdict(list)
    for run in runs[:10]:
        for task_run in run.task_runs:
            failures_by_task[task_run.task_id].append(task_run)

    for task_id, task_runs in failures_by_task.items():
        consecutive = 0
        for task_run in task_runs:
            if task_run.state in FAILURE_STATES:
                consecutive += 1
            else:
                break
        if consecutive >= 2:
            latest = task_runs[0]
            title = f"{task_id} is failing repeatedly"
            _upsert_incident(
                db,
                workspace_id=workspace_id,
                dag_id=dag_id,
                task_id=task_id,
                title=title,
                severity="high",
                error_summary=latest.error_summary,
                consecutive_failures=consecutive,
                first_seen_at=task_runs[consecutive - 1].start_time or task_runs[consecutive - 1].created_at,
                last_seen_at=latest.end_time or latest.start_time or latest.created_at,
            )
            active.add((dag_id, task_id, title))
    return active


def _create_duration_recommendations(db: Session, workspace_id: str, dag_id: str, runs: list[DagRun]) -> set[tuple[str, str | None, str]]:
    active: set[tuple[str, str | None, str]] = set()
    complete_runs = [run for run in runs if run.duration_seconds and run.duration_seconds > 0]
    if len(complete_runs) >= 4:
        latest = complete_runs[0]
        baseline_values = [run.duration_seconds for run in complete_runs[1:10] if run.duration_seconds]
        baseline = median(baseline_values) if baseline_values else None
        if baseline and latest.duration_seconds and latest.duration_seconds > baseline * 1.4:
            _upsert_recommendation(
                db,
                workspace_id=workspace_id,
                dag_id=dag_id,
                task_id=None,
                kind="duration_anomaly",
                title=f"{dag_id} runtime is above baseline",
                impact="high",
                reason=f"Latest run took {latest.duration_seconds:.0f}s versus a median baseline of {baseline:.0f}s.",
                evidence_count=len(baseline_values) + 1,
                estimated_savings_seconds=max(latest.duration_seconds - baseline, 0),
                score=90.0,
            )
            active.add((dag_id, None, "duration_anomaly"))

    slow_task_evidence: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for run in runs[:10]:
        total = run.duration_seconds or sum(task.duration_seconds or 0 for task in run.task_runs)
        if not total:
            continue
        for task in run.task_runs:
            if task.duration_seconds and task.duration_seconds / total >= 0.60:
                slow_task_evidence[task.task_id].append((task.duration_seconds / total * 100, task.duration_seconds))
                break

    for task_id, evidence in slow_task_evidence.items():
        percentages = [item[0] for item in evidence]
        task_durations = [item[1] for item in evidence]
        avg_pct = sum(percentages) / len(percentages)
        max_pct = max(percentages)
        avg_task_duration = sum(task_durations) / len(task_durations)
        estimated_savings = avg_task_duration * 0.2
        _upsert_recommendation(
            db,
            workspace_id=workspace_id,
            dag_id=dag_id,
            task_id=task_id,
            kind="slow_task",
            title=f"Optimize {task_id}",
            impact="critical" if max_pct >= 85 and len(evidence) >= 3 else "high" if max_pct >= 70 else "medium",
            reason=(
                f"{task_id} dominated {len(evidence)} recent runs, averaging {avg_pct:.0f}% "
                f"of DAG runtime. A 20% improvement would save about {estimated_savings:.0f}s per run."
            ),
            evidence_count=len(evidence),
            estimated_savings_seconds=estimated_savings,
            score=min(100.0, max_pct + min(len(evidence), 10)),
        )
        active.add((dag_id, task_id, "slow_task"))

    retry_counts: dict[str, int] = defaultdict(int)
    for run in runs[:10]:
        for task in run.task_runs:
            if task.try_number > 1:
                retry_counts[task.task_id] += task.try_number - 1

    for task_id, retries in retry_counts.items():
        if retries >= 3:
            _upsert_recommendation(
                db,
                workspace_id=workspace_id,
                dag_id=dag_id,
                task_id=task_id,
                kind="retry_policy",
                title=f"Review retry policy for {task_id}",
                impact="medium",
                reason=f"{task_id} accumulated {retries} retries in the latest observed runs.",
                evidence_count=retries,
                estimated_savings_seconds=None,
                score=50.0 + retries,
            )
            active.add((dag_id, task_id, "retry_policy"))
    return active


def _create_metadata_recommendations(db: Session, workspace_id: str, dag: Dag) -> set[tuple[str, str | None, str]]:
    active: set[tuple[str, str | None, str]] = set()
    if not dag.owner:
        _upsert_recommendation(
            db,
            workspace_id=workspace_id,
            dag_id=dag.dag_id,
            task_id=None,
            kind="missing_owner",
            title=f"Add an owner to {dag.dag_id}",
            impact="low",
            reason="DAG ownership is missing, which makes incident routing slower.",
            evidence_count=1,
            estimated_savings_seconds=None,
            score=25.0,
        )
        active.add((dag.dag_id, None, "missing_owner"))
    if not dag.tags or dag.tags == "[]":
        _upsert_recommendation(
            db,
            workspace_id=workspace_id,
            dag_id=dag.dag_id,
            task_id=None,
            kind="missing_tags",
            title=f"Add tags to {dag.dag_id}",
            impact="low",
            reason="Tags make it easier to group pipelines by domain or team.",
            evidence_count=1,
            estimated_savings_seconds=None,
            score=20.0,
        )
        active.add((dag.dag_id, None, "missing_tags"))
    return active


def _upsert_incident(
    db: Session,
    workspace_id: str,
    dag_id: str,
    task_id: str | None,
    title: str,
    severity: str,
    error_summary: str | None,
    consecutive_failures: int,
    first_seen_at: datetime,
    last_seen_at: datetime,
) -> None:
    incident = (
        db.query(Incident)
        .filter(
            Incident.workspace_id == workspace_id,
            Incident.dag_id == dag_id,
            Incident.task_id.is_(None) if task_id is None else Incident.task_id == task_id,
            Incident.title == title,
        )
        .one_or_none()
    )
    if incident is None:
        incident = Incident(
            workspace_id=workspace_id,
            dag_id=dag_id,
            task_id=task_id,
            title=title,
            first_seen_at=first_seen_at,
        )
        db.add(incident)
    elif incident.status == "resolved":
        incident.status = "open"
    incident.severity = severity
    incident.error_summary = error_summary
    incident.consecutive_failures = consecutive_failures
    incident.last_seen_at = last_seen_at


def _upsert_recommendation(
    db: Session,
    workspace_id: str,
    dag_id: str,
    task_id: str | None,
    kind: str,
    title: str,
    impact: str,
    reason: str,
    evidence_count: int,
    estimated_savings_seconds: float | None,
    score: float,
) -> None:
    recommendation = (
        db.query(Recommendation)
        .filter(
            Recommendation.workspace_id == workspace_id,
            Recommendation.dag_id == dag_id,
            Recommendation.task_id.is_(None) if task_id is None else Recommendation.task_id == task_id,
            Recommendation.kind == kind,
        )
        .one_or_none()
    )
    if recommendation is None:
        recommendation = Recommendation(workspace_id=workspace_id, dag_id=dag_id, task_id=task_id, kind=kind)
        db.add(recommendation)
    recommendation.title = title
    recommendation.impact = impact
    recommendation.reason = reason
    recommendation.evidence_count = evidence_count
    recommendation.estimated_savings_seconds = estimated_savings_seconds
    recommendation.score = score
    recommendation.status = "active"


def _resolve_stale_incidents(
    db: Session,
    workspace_id: str,
    active_incidents: set[tuple[str, str | None, str]],
) -> None:
    now = datetime.now(UTC)
    incidents = db.query(Incident).filter(Incident.workspace_id == workspace_id, Incident.status == "open").all()
    for incident in incidents:
        key = (incident.dag_id, incident.task_id, incident.title)
        if key not in active_incidents:
            incident.status = "resolved"
            incident.last_seen_at = now


def _resolve_stale_recommendations(
    db: Session,
    workspace_id: str,
    active_recommendations: set[tuple[str, str | None, str]],
) -> None:
    recommendations = (
        db.query(Recommendation)
        .filter(Recommendation.workspace_id == workspace_id, Recommendation.status == "active")
        .all()
    )
    for recommendation in recommendations:
        key = (recommendation.dag_id, recommendation.task_id, recommendation.kind)
        if key not in active_recommendations:
            recommendation.status = "resolved"


def get_overview(db: Session, workspace_id: str) -> dict:
    dag_count = db.query(func.count(Dag.id)).filter(Dag.workspace_id == workspace_id).scalar() or 0
    runs = db.query(DagRun).filter(DagRun.workspace_id == workspace_id).order_by(desc(DagRun.execution_date), desc(DagRun.id)).limit(200).all()
    durations = [run.duration_seconds for run in runs if run.duration_seconds is not None]
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    seven_days_ago = datetime.now(UTC) - timedelta(days=7)
    recent_runs = [
        run
        for run in runs
        if _observed_at(run) >= seven_days_ago
    ]
    today_failures = [
        run
        for run in runs
        if run.state in FAILURE_STATES and _observed_at(run) >= today_start
    ]
    incidents = db.query(func.count(Incident.id)).filter(Incident.workspace_id == workspace_id, Incident.status == "open").scalar() or 0
    top_recommendations = (
        db.query(Recommendation)
        .filter(Recommendation.workspace_id == workspace_id, Recommendation.status == "active")
        .order_by(desc(Recommendation.score))
        .limit(5)
        .all()
    )
    agents = (
        db.query(AirflowInstance)
        .filter(AirflowInstance.workspace_id == workspace_id, AirflowInstance.agent_version.isnot(None))
        .order_by(desc(AirflowInstance.last_heartbeat_at))
        .all()
    )

    latest_by_dag: dict[int, DagRun] = {}
    for run in runs:
        latest_by_dag.setdefault(run.dag_id_fk, run)

    return {
        "active_dags": dag_count,
        "failed_dags_today": len({run.dag_id_fk for run in today_failures}),
        "success_rate_7d": round(
            len([run for run in recent_runs if run.state in SUCCESS_STATES]) / len(recent_runs) * 100,
            1,
        )
        if recent_runs
        else 0.0,
        "avg_duration_seconds": round(sum(durations) / len(durations), 1) if durations else 0.0,
        "p95_duration_seconds": percentile(durations, 0.95) or 0.0,
        "open_incidents": incidents,
        "agents": [_agent_payload(agent) for agent in agents],
        "top_recommendations": [_recommendation_payload(item) for item in top_recommendations],
        "latest_runs": [
            {
                "dag_id": run.dag.dag_id,
                "run_id": run.run_id,
                "state": run.state,
                "duration_seconds": run.duration_seconds,
                "execution_date": run.execution_date,
            }
            for run in latest_by_dag.values()
        ],
    }


def _agent_payload(agent: AirflowInstance) -> dict:
    last_seen = agent.last_heartbeat_at
    seconds_since_seen = None
    status = "never_seen"
    if last_seen:
        now = datetime.now(UTC)
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=UTC)
        seconds_since_seen = max((now - last_seen).total_seconds(), 0)
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


def _observed_at(run: DagRun) -> datetime:
    value = run.execution_date or run.start_time or run.created_at
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


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
