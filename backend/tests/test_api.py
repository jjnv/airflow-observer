from datetime import UTC, datetime, timedelta
import os

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.core.config import get_settings
from app.models.entities import ApiKey, DagRun, Incident, Workspace


def make_client():
    os.environ["DEMO_MODE"] = "true"
    get_settings.cache_clear()
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    db.add(Workspace(id="demo-workspace", name="Demo"))
    db.add(ApiKey(workspace_id="demo-workspace", key="test-key", name="test"))
    db.commit()
    db.close()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), TestingSessionLocal


def snapshot_payload(with_failures: bool = True):
    base = datetime.now(UTC).replace(hour=8, minute=0, second=0, microsecond=0)
    runs = []
    for idx, duration in enumerate([900, 610, 600, 590]):
        start = base - timedelta(days=idx)
        end = start + timedelta(seconds=duration)
        state = "failed" if with_failures and idx in {0, 1} else "success"
        runs.append(
            {
                "run_id": f"scheduled__{idx}",
                "state": state,
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
                "execution_date": start.isoformat(),
                "tasks": [
                    {
                        "task_id": "extract_orders",
                        "state": state,
                        "try_number": 2 if idx == 0 else 1,
                        "start_time": start.isoformat(),
                        "end_time": (start + timedelta(seconds=120)).isoformat(),
                        "error_summary": "Timeout connecting to source API" if state == "failed" else None,
                    },
                    {
                        "task_id": "load_to_redshift",
                        "state": "success",
                        "try_number": 1,
                        "start_time": (start + timedelta(seconds=120)).isoformat(),
                        "end_time": end.isoformat(),
                    },
                ],
            }
        )
    return {
        "workspace_id": "demo-workspace",
        "airflow_instance_uid": "local-airflow",
        "airflow_instance_name": "Local Airflow",
        "airflow_base_url": "http://airflow:8080",
        "collected_at": base.isoformat(),
        "dags": [
            {
                "dag_id": "customer_orders_etl",
                "owner": "data-eng",
                "tags": ["warehouse"],
                "is_active": True,
                "is_paused": False,
                "runs": runs,
            }
        ],
    }


def test_ingest_snapshot_is_idempotent_and_recomputes_analytics():
    client, SessionLocal = make_client()
    headers = {"X-API-Key": "test-key"}

    first = client.post("/api/v1/ingest/snapshot", json=snapshot_payload(), headers=headers)
    second = client.post("/api/v1/ingest/snapshot", json=snapshot_payload(), headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["ingested"] == {"dags": 1, "dag_runs": 4, "task_runs": 8}

    db = SessionLocal()
    try:
        assert db.query(DagRun).count() == 4
    finally:
        db.close()

    overview = client.get("/api/v1/overview")
    assert overview.status_code == 200
    assert overview.json()["active_dags"] == 1
    assert overview.json()["failed_dags_today"] == 1
    assert overview.json()["success_rate_7d"] == 50.0
    assert overview.json()["open_incidents"] >= 1

    recommendations = client.get("/api/v1/recommendations").json()["recommendations"]
    assert any("runtime is above baseline" in item["title"] for item in recommendations)
    assert any(item["task_id"] == "load_to_redshift" for item in recommendations)

    incidents = client.get("/api/v1/incidents").json()["incidents"]
    assert any(item["dag_id"] == "customer_orders_etl" for item in incidents)


def test_incidents_preserve_first_seen_and_resolve_when_evidence_clears():
    client, SessionLocal = make_client()
    headers = {"X-API-Key": "test-key"}

    assert client.post("/api/v1/ingest/snapshot", json=snapshot_payload(), headers=headers).status_code == 200

    db = SessionLocal()
    try:
        incident = db.query(Incident).filter(Incident.dag_id == "customer_orders_etl").first()
        assert incident is not None
        first_seen = incident.first_seen_at
    finally:
        db.close()

    assert client.post("/api/v1/ingest/snapshot", json=snapshot_payload(), headers=headers).status_code == 200

    db = SessionLocal()
    try:
        incident = db.query(Incident).filter(Incident.dag_id == "customer_orders_etl").first()
        assert incident.first_seen_at == first_seen
        assert incident.status == "open"
    finally:
        db.close()

    assert client.post("/api/v1/ingest/snapshot", json=snapshot_payload(with_failures=False), headers=headers).status_code == 200

    assert client.get("/api/v1/incidents").json()["incidents"] == []
    db = SessionLocal()
    try:
        assert {item.status for item in db.query(Incident).all()} == {"resolved"}
    finally:
        db.close()


def test_rejects_invalid_api_key():
    client, _ = make_client()
    response = client.post("/api/v1/ingest/snapshot", json=snapshot_payload(), headers={"X-API-Key": "bad"})

    assert response.status_code == 401


def test_onboarding_does_not_expose_api_key():
    client, _ = make_client()
    response = client.get("/api/v1/onboarding")

    assert response.status_code == 200
    payload = response.json()
    assert "default_api_key_hint" not in payload
    assert payload["api_key_env_var"] == "OBSERVER_API_KEY"
