"""Backfill historical weather data DAG."""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator

default_args = {
    "owner": "weather-intelligence",
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
    "start_date": datetime(2024, 1, 1),
}

dag = DAG(
    dag_id="weather_etl_backfill",
    default_args=default_args,
    description="Backfill historical weather data from Open-Meteo",
    schedule_interval=None,  # Triggered manually
    catchup=False,
    tags=["weather", "etl", "backfill"],
)

# TODO: Implement backfill logic with parameterized date ranges
start = EmptyOperator(task_id="start", dag=dag)
end = EmptyOperator(task_id="end", dag=dag)

start >> end
