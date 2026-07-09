from __future__ import annotations

import time
from datetime import datetime, timedelta

from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator


DEFAULT_ARGS = {
    "owner": "data-eng",
    "retries": 0,
}


def sleep_for(seconds: int) -> None:
    time.sleep(seconds)


def fail_with_timeout() -> None:
    raise AirflowException("Timeout connecting to source API")


def fail_then_retry(**context) -> None:
    if context["ti"].try_number == 1:
        raise AirflowException("Synthetic transient warehouse lock")


with DAG(
    dag_id="observer_success_dag",
    start_date=datetime(2026, 7, 1),
    schedule="@hourly",
    catchup=False,
    tags=["observer", "healthy"],
    default_args=DEFAULT_ARGS,
) as success_dag:
    EmptyOperator(task_id="extract")
    EmptyOperator(task_id="transform")
    EmptyOperator(task_id="load")


with DAG(
    dag_id="observer_slow_dag",
    start_date=datetime(2026, 7, 1),
    schedule="@daily",
    catchup=False,
    tags=["observer", "slow"],
    default_args=DEFAULT_ARGS,
) as slow_dag:
    PythonOperator(task_id="extract", python_callable=sleep_for, op_args=[2])
    PythonOperator(task_id="load_to_redshift", python_callable=sleep_for, op_args=[12])


with DAG(
    dag_id="observer_failing_dag",
    start_date=datetime(2026, 7, 1),
    schedule="@daily",
    catchup=False,
    tags=["observer", "failing"],
    default_args=DEFAULT_ARGS,
) as failing_dag:
    EmptyOperator(task_id="start")
    PythonOperator(task_id="extract_orders", python_callable=fail_with_timeout)


with DAG(
    dag_id="observer_retry_dag",
    start_date=datetime(2026, 7, 1),
    schedule="@daily",
    catchup=False,
    tags=["observer", "retries"],
    default_args={"owner": "platform", "retries": 1, "retry_delay": timedelta(seconds=5)},
) as retry_dag:
    PythonOperator(task_id="warehouse_load", python_callable=fail_then_retry)


with DAG(
    dag_id="observer_degraded_dag",
    start_date=datetime(2026, 7, 1),
    schedule="@daily",
    catchup=False,
    tags=["observer", "degraded"],
    default_args={"retries": 0},
) as degraded_dag:
    PythonOperator(task_id="api_extract", python_callable=sleep_for, op_args=[1])
    PythonOperator(task_id="normalize_payloads", python_callable=sleep_for, op_args=[2])
    PythonOperator(task_id="publish_metrics", python_callable=sleep_for, op_args=[8])
