import argparse
import json
import logging
from pathlib import Path
import time

from airflow_observer_agent.airflow_client import AirflowClient
from airflow_observer_agent.config import AgentConfig
from airflow_observer_agent.observer_client import ObserverClient
from airflow_observer_agent.snapshot import build_snapshot


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("airflow-observer-agent")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Airflow metadata and send it to Airflow Observer.")
    parser.add_argument("--once", action="store_true", help="Collect and send one snapshot, then exit.")
    parser.add_argument("--dry-run", action="store_true", help="Print one snapshot without sending it to Observer.")
    return parser.parse_args()


def collect_once(config: AgentConfig, dry_run: bool = False) -> dict:
    airflow_client = AirflowClient(config)
    snapshot = build_snapshot(config, airflow_client)
    if dry_run:
        print(json.dumps(snapshot, indent=2))
        return {"ok": True, "dry_run": True, "dags": len(snapshot["dags"])}
    observer_client = ObserverClient(config)
    result = observer_client.post_snapshot(snapshot)
    _write_heartbeat()
    logger.info(
        "Posted snapshot: dags=%s dag_runs=%s task_runs=%s",
        result.get("ingested", {}).get("dags"),
        result.get("ingested", {}).get("dag_runs"),
        result.get("ingested", {}).get("task_runs"),
    )
    return result


def main() -> None:
    args = parse_args()
    config = AgentConfig.from_env()
    while True:
        collect_once(config, dry_run=args.dry_run)
        if args.once or args.dry_run:
            break
        time.sleep(config.poll_interval_seconds)


def _write_heartbeat() -> None:
    Path("/tmp/airflow-observer-agent-heartbeat").write_text(str(time.time()), encoding="utf-8")


if __name__ == "__main__":
    main()
