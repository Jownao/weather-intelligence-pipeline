"""Setup scripts for BigQuery infrastructure."""

import json
import logging
import os
from pathlib import Path

from google.cloud import bigquery
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)


def _configure_credentials_path() -> None:
    """Prefer a real local key file when running outside the container."""
    configured_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if configured_path and Path(configured_path).exists():
        return

    fallback_path = os.getenv("GCP_KEY_PATH")
    if fallback_path and Path(fallback_path).exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = fallback_path
        logger.info(f"Using local GCP key at {fallback_path}")
        return

    raise FileNotFoundError(
        "No valid GCP credentials file found. Set GOOGLE_APPLICATION_CREDENTIALS "
        "or GCP_KEY_PATH to an existing JSON key file."
    )


def _get_partition_field(schema: list[bigquery.SchemaField]) -> str | None:
    """Return the best partition field available for the table schema."""
    schema_fields = {field.name for field in schema}
    if "date" in schema_fields:
        return "date"
    if "metric_date" in schema_fields:
        return "metric_date"
    return None


def setup_bigquery():
    """Create datasets and tables in BigQuery with proper schemas."""
    project_id = os.getenv("GCP_PROJECT_ID")
    if not project_id:
        raise ValueError("GCP_PROJECT_ID not set in environment")

    _configure_credentials_path()

    client = bigquery.Client(project=project_id)

    # Datasets to create
    datasets = [
        ("weather_bronze", "Raw weather data from Open-Meteo API"),
        ("weather_silver", "Cleaned and transformed weather data"),
        ("weather_gold", "Aggregated analytics-ready data"),
    ]

    # Create datasets
    for dataset_name, description in datasets:
        dataset_id = f"{project_id}.{dataset_name}"
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = os.getenv("GCP_REGION", "US")
        dataset.description = description

        try:
            existing = client.get_dataset(dataset_id)
            logger.info(f"Dataset {dataset_id} already exists")
        except Exception:
            client.create_dataset(dataset)
            logger.info(f"Created dataset {dataset_id}")

    # Create tables from schema files
    schema_dir = PROJECT_ROOT / "config" / "schema"

    tables_config = [
        ("weather_bronze", "weather_raw", schema_dir / "bronze_schema.json"),
        ("weather_silver", "weather_cleaned", schema_dir / "silver_schema.json"),
        ("weather_gold", "weather_aggregates", schema_dir / "gold_schema.json"),
    ]

    for dataset, table_name, schema_file in tables_config:
        if not schema_file.exists():
            logger.warning(f"Schema file not found: {schema_file}")
            continue

        table_id = f"{project_id}.{dataset}.{table_name}"

        try:
            # Check if table exists
            client.get_table(table_id)
            logger.info(f"Table {table_id} already exists")
        except Exception:
            # Load schema
            with open(schema_file, "r") as f:
                schema_dict = json.load(f)

            schema = [
                bigquery.SchemaField.from_api_repr(field)
                for field in schema_dict.get("fields", [])
            ]

            # Create table
            table = bigquery.Table(table_id, schema=schema)
            partition_field = _get_partition_field(schema)
            if partition_field:
                table.time_partitioning = bigquery.TimePartitioning(
                    type_=bigquery.TimePartitioningType.DAY, field=partition_field
                )
            client.create_table(table)
            logger.info(f"Created table {table_id}")

    logger.info("✅ BigQuery setup completed successfully!")


if __name__ == "__main__":
    setup_bigquery()
