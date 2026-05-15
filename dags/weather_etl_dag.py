"""Main daily weather ETL DAG."""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator

# Default arguments
default_args = {
    "owner": "weather-intelligence",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "start_date": datetime(2024, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
}

# DAG definition
dag = DAG(
    dag_id="weather_etl_daily",
    default_args=default_args,
    description="Daily weather data ETL pipeline - Extract from Open-Meteo, Load to BigQuery",
    schedule_interval="0 2 * * *",  # 02:00 UTC daily
    catchup=False,
    tags=["weather", "etl", "production"],
)


def extract_weather_data(**context):
    """Extract weather data from Open-Meteo API."""
    import os
    import logging

    from pipeline.extractors.open_meteo import OpenMeteoClient

    logger = logging.getLogger(__name__)
    logger.info("Starting weather data extraction...")

    # Initialize client
    client = OpenMeteoClient()

    # Sample extraction for São Paulo (hardcoded for now, make dynamic with Airflow variables)
    try:
        data = client.get_last_30_days(latitude=-23.5505, longitude=-46.6333)
        logger.info(f"Successfully extracted data: {len(data.get('daily', {}).get('time', []))} days")
        context["task_instance"].xcom_push(key="raw_data", value=data)
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise


def transform_weather_data(**context):
    """Transform and clean extracted weather data."""
    import logging
    from datetime import datetime

    from pipeline.transformers.weather_transformer import WeatherTransformer

    logger = logging.getLogger(__name__)
    logger.info("Starting data transformation...")

    # Get raw data from previous task
    raw_data = context["task_instance"].xcom_pull(task_ids="extract_weather", key="raw_data")

    if not raw_data:
        logger.warning("No raw data found to transform")
        return

    # Transform
    df = WeatherTransformer.transform_open_meteo_response(
        api_response=raw_data,
        region_name="São Paulo",
        region_code="SP",
        extraction_timestamp=datetime.utcnow(),
    )

    # Clean
    df_clean, metrics = WeatherTransformer.clean_weather_data(df)
    logger.info(f"Transformation metrics: {metrics}")

    # XCom needs JSON-serializable data, so normalize datetime-like fields first.
    df_payload = df_clean.copy()
    for column in ["date", "extraction_timestamp", "load_timestamp"]:
        if column in df_payload.columns:
            df_payload[column] = df_payload[column].astype(str)

    context["task_instance"].xcom_push(
        key="transformed_data", value=df_payload.to_dict(orient="records")
    )


def load_to_bigquery(**context):
    """Load cleaned data to BigQuery Bronze layer."""
    import logging
    from pandas import DataFrame

    from pipeline.loaders.bigquery_loader import BigQueryLoader

    logger = logging.getLogger(__name__)
    logger.info("Starting BigQuery load...")

    # Get transformed data
    data_dict = context["task_instance"].xcom_pull(
        task_ids="transform_weather", key="transformed_data"
    )

    if not data_dict:
        logger.warning("No transformed data found to load")
        return

    df = DataFrame(data_dict)

    # Bronze schema is narrower than the transformed dataframe.
    bronze_columns = [
        "extraction_timestamp",
        "region_name",
        "latitude",
        "longitude",
        "date",
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation_sum",
        "windspeed_10m",
        "cloudcover",
        "raw_response",
        "load_timestamp",
    ]
    for column in bronze_columns:
        if column not in df.columns:
            df[column] = None
    df = df[bronze_columns]

    # Initialize loader
    loader = BigQueryLoader()

    # Load to Bronze
    job_id = loader.load_to_bronze(df, table_name="weather_raw")
    logger.info(f"Load job completed: {job_id}")


# Tasks
start_task = EmptyOperator(task_id="start", dag=dag)

extract_task = PythonOperator(
    task_id="extract_weather",
    python_callable=extract_weather_data,
    dag=dag,
)

transform_task = PythonOperator(
    task_id="transform_weather",
    python_callable=transform_weather_data,
    dag=dag,
)

load_task = PythonOperator(
    task_id="load_bigquery",
    python_callable=load_to_bigquery,
    dag=dag,
)

end_task = EmptyOperator(task_id="end", dag=dag)

# Define dependencies
start_task >> extract_task >> transform_task >> load_task >> end_task
