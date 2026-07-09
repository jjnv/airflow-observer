from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path


BASE_DATE = datetime(2026, 7, 9, 8, 0, tzinfo=UTC)
RUN_COUNT = 15


def iso(value: datetime) -> str:
    return value.isoformat()


def task(task_id: str, state: str, start: datetime, seconds: int, try_number: int = 1, error: str | None = None) -> dict:
    return {
        "task_id": task_id,
        "state": state,
        "try_number": try_number,
        "start_time": iso(start),
        "end_time": iso(start + timedelta(seconds=seconds)),
        "error_summary": error,
    }


def customer_orders_runs() -> list[dict]:
    runs = []
    durations = [900, 620, 590, 605, 615, 580, 610, 600, 595, 625, 585, 610, 600, 590, 605]
    for idx, duration in enumerate(durations):
        start = BASE_DATE - timedelta(days=idx)
        state = "failed" if idx in {0, 1} else "success"
        extract_seconds = 180 if state == "failed" else 120
        load_seconds = max(duration - extract_seconds, 60)
        runs.append(
            {
                "run_id": f"scheduled__{start.date()}",
                "state": state,
                "start_time": iso(start),
                "end_time": iso(start + timedelta(seconds=duration)),
                "execution_date": iso(start),
                "tasks": [
                    task(
                        "extract_orders",
                        state,
                        start,
                        extract_seconds,
                        try_number=2 if idx == 0 else 1,
                        error="Timeout connecting to source API" if state == "failed" else None,
                    ),
                    task("load_to_redshift", "success", start + timedelta(seconds=extract_seconds), load_seconds),
                ],
            }
        )
    return runs


def jira_ingestion_runs() -> list[dict]:
    runs = []
    durations = [1200, 760, 720, 690, 710, 740, 680, 705, 715, 690, 730, 700, 710, 695, 725]
    for idx, duration in enumerate(durations):
        start = BASE_DATE.replace(hour=7) - timedelta(days=idx)
        fetch_seconds = 300 if idx in {0, 4, 8, 12} else 180
        sync_seconds = max(duration - fetch_seconds, 90)
        runs.append(
            {
                "run_id": f"scheduled__{start.date()}",
                "state": "success",
                "start_time": iso(start),
                "end_time": iso(start + timedelta(seconds=duration)),
                "execution_date": iso(start),
                "tasks": [
                    task("fetch_issues", "success", start, fetch_seconds, try_number=4 if idx == 0 else 2 if idx in {4, 8, 12} else 1),
                    task("sync_warehouse", "success", start + timedelta(seconds=fetch_seconds), sync_seconds),
                ],
            }
        )
    return runs


def marketing_export_runs() -> list[dict]:
    runs = []
    durations = [120, 118, 122, 125, 119, 121, 117, 123, 126, 120, 118, 124, 119, 121, 116]
    for idx, duration in enumerate(durations):
        start = BASE_DATE.replace(hour=9) - timedelta(days=idx)
        runs.append(
            {
                "run_id": f"manual__{start.date()}",
                "state": "success",
                "start_time": iso(start),
                "end_time": iso(start + timedelta(seconds=duration)),
                "execution_date": iso(start),
                "tasks": [
                    task("export_csv", "success", start, duration),
                ],
            }
        )
    return runs


def build_snapshot() -> dict:
    return {
        "workspace_id": "demo-workspace",
        "airflow_instance_uid": "seed-airflow",
        "airflow_instance_name": "Seeded Demo Airflow",
        "airflow_base_url": "http://airflow:8080",
        "collected_at": "2026-07-09T08:30:00+00:00",
        "dags": [
            {
                "dag_id": "customer_orders_etl",
                "owner": "data-eng",
                "tags": ["warehouse", "orders"],
                "is_active": True,
                "is_paused": False,
                "runs": customer_orders_runs(),
            },
            {
                "dag_id": "jira_ingestion",
                "owner": "analytics",
                "tags": ["saas", "support"],
                "is_active": True,
                "is_paused": False,
                "runs": jira_ingestion_runs(),
            },
            {
                "dag_id": "unowned_marketing_export",
                "owner": None,
                "tags": [],
                "is_active": True,
                "is_paused": False,
                "runs": marketing_export_runs(),
            },
        ],
    }


def main() -> None:
    output_path = Path(__file__).with_name("demo_snapshot.json")
    output_path.write_text(json.dumps(build_snapshot(), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
