"""BigQuery data loader for Bronze, Silver, and Gold layers."""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import pandas as pd
from google.cloud import bigquery
from google.cloud.bigquery import LoadJobConfig, SchemaField
from google.cloud.exceptions import GoogleCloudError

logger = logging.getLogger(__name__)


class BigQueryLoader:
    """Load data to BigQuery with support for different data layers."""

    def __init__(
        self,
        project_id: Optional[str] = None,
        dataset_bronze: Optional[str] = None,
        dataset_silver: Optional[str] = None,
        dataset_gold: Optional[str] = None,
        location: Optional[str] = None,
    ):
        """Initialize BigQuery loader.

        Args:
            project_id: GCP project ID (from env if None)
            dataset_bronze: Bronze layer dataset name
            dataset_silver: Silver layer dataset name
            dataset_gold: Gold layer dataset name
            location: BigQuery location
        """
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        self.dataset_bronze = dataset_bronze or os.getenv("GCP_DATASET_BRONZE", "weather_bronze")
        self.dataset_silver = dataset_silver or os.getenv("GCP_DATASET_SILVER", "weather_silver")
        self.dataset_gold = dataset_gold or os.getenv("GCP_DATASET_GOLD", "weather_gold")
        self.location = location or os.getenv("GCP_REGION", "US")

        self.client = bigquery.Client(project=self.project_id, location=self.location)

        logger.info(
            f"BigQueryLoader initialized: project={self.project_id}, "
            f"location={self.location}, bronze={self.dataset_bronze}"
        )

    def load_to_bronze(
        self,
        df: pd.DataFrame,
        table_name: str = "weather_raw",
        if_exists: str = "append",
    ) -> str:
        """Load raw data to Bronze layer.

        Args:
            df: DataFrame with raw data
            table_name: Target table name
            if_exists: 'append' or 'replace'

        Returns:
            Load job ID
        """
        return self._load_to_dataset(
            df=df, dataset=self.dataset_bronze, table_name=table_name, if_exists=if_exists
        )

    def load_to_silver(
        self,
        df: pd.DataFrame,
        table_name: str = "weather_cleaned",
        if_exists: str = "append",
    ) -> str:
        """Load cleaned data to Silver layer.

        Args:
            df: DataFrame with cleaned data
            table_name: Target table name
            if_exists: 'append' or 'replace'

        Returns:
            Load job ID
        """
        return self._load_to_dataset(
            df=df, dataset=self.dataset_silver, table_name=table_name, if_exists=if_exists
        )

    def load_to_gold(
        self,
        df: pd.DataFrame,
        table_name: str = "weather_aggregates",
        if_exists: str = "append",
    ) -> str:
        """Load aggregated data to Gold layer.

        Args:
            df: DataFrame with aggregated data
            table_name: Target table name
            if_exists: 'append' or 'replace'

        Returns:
            Load job ID
        """
        return self._load_to_dataset(
            df=df, dataset=self.dataset_gold, table_name=table_name, if_exists=if_exists
        )

    def _load_to_dataset(
        self,
        df: pd.DataFrame,
        dataset: str,
        table_name: str,
        if_exists: str = "append",
    ) -> str:
        """Internal method to load DataFrame to BigQuery.

        Args:
            df: DataFrame to load
            dataset: Target dataset
            table_name: Target table
            if_exists: 'append' or 'replace'

        Returns:
            Load job ID
        """
        if df.empty:
            logger.warning(f"Skipping load: empty DataFrame for {dataset}.{table_name}")
            return "EMPTY"

        # Make sure the target dataset exists before attempting the load.
        self.create_dataset_if_not_exists(dataset)

        table_id = f"{self.project_id}.{dataset}.{table_name}"

        try:
            # Normalize only known temporal fields to avoid converting string columns
            # (e.g. raw_response) into datetime by mistake.
            date_columns = {"date", "metric_date"}
            timestamp_columns = {
                "extraction_timestamp",
                "load_timestamp",
                "transformation_timestamp",
                "aggregation_timestamp",
            }

            for col in df.columns:
                if col in date_columns:
                    df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
                elif col in timestamp_columns:
                    df[col] = pd.to_datetime(df[col], errors="coerce")

            if "raw_response" in df.columns:
                df["raw_response"] = df["raw_response"].where(
                    df["raw_response"].isna(), df["raw_response"].astype(str)
                )

            # Validate dataframe against schema if available
            try:
                self.validate_df_schema(df, dataset, table_name)
            except ValueError as e:
                logger.error(f"Schema validation failed for {table_id}: {e}")
                raise

            job_config = LoadJobConfig(
                write_disposition=(
                    "WRITE_APPEND" if if_exists == "append" else "WRITE_TRUNCATE"
                ),
                autodetect=False,  # We'll use schemas from config
            )

            logger.info(f"Loading {len(df)} rows to {table_id}")
            load_job = self.client.load_table_from_dataframe(df, table_id, job_config=job_config)

            load_job.result()  # Wait for job to complete

            logger.info(f"Successfully loaded to {table_id}. Job ID: {load_job.job_id}")
            return load_job.job_id

        except GoogleCloudError as e:
            logger.error(f"Error loading data to {table_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading data: {e}")
            raise

    def create_dataset_if_not_exists(self, dataset: str) -> None:
        """Create BigQuery dataset if it doesn't exist.

        Args:
            dataset: Dataset name
        """
        dataset_id = f"{self.project_id}.{dataset}"

        try:
            self.client.get_dataset(dataset_id)
            logger.info(f"Dataset {dataset_id} already exists")
        except Exception:
            dataset_obj = bigquery.Dataset(dataset_id)
            dataset_obj.location = self.location
            self.client.create_dataset(dataset_obj)
            logger.info(f"Created dataset {dataset_id}")

    def create_table_from_schema(
        self,
        dataset: str,
        table_name: str,
        schema_file: str,
        if_exists: str = "ignore",
    ) -> None:
        """Create table in BigQuery from JSON schema file.

        Args:
            dataset: Target dataset
            table_name: Target table
            schema_file: Path to JSON schema file
            if_exists: 'ignore' or 'replace'
        """
        table_id = f"{self.project_id}.{dataset}.{table_name}"

        try:
            # Load schema from JSON file
            with open(schema_file, "r") as f:
                schema_dict = json.load(f)

            schema = [
                SchemaField.from_api_repr(field) for field in schema_dict.get("fields", [])
            ]

            # Check if table exists
            try:
                self.client.get_table(table_id)
                if if_exists == "ignore":
                    logger.info(f"Table {table_id} already exists, skipping")
                    return
                else:
                    self.client.delete_table(table_id)
                    logger.info(f"Deleted existing table {table_id}")
            except Exception:
                pass

            table = bigquery.Table(table_id, schema=schema)
            table.time_partitioning = bigquery.TimePartitioning(
                type_=bigquery.TimePartitioningType.DAY, field="date"
            )
            self.client.create_table(table)
            logger.info(f"Created table {table_id}")

        except Exception as e:
            logger.error(f"Error creating table from schema: {e}")
            raise

    def validate_df_schema(self, df: pd.DataFrame, dataset: str, table_name: str) -> None:
        """Validate a DataFrame against the JSON schema in `config/schema`.

        This performs basic checks:
        - required fields present
        - attempts to coerce types for DATE/TIMESTAMP/NUMERIC fields

        Raises:
            ValueError: if required columns are missing or coercion fails
        """
        # Map dataset to schema filename
        base = os.path.join(os.getcwd(), "config", "schema")
        schema_file = None
        ds = dataset.lower()
        if "bronze" in ds:
            schema_file = os.path.join(base, "bronze_schema.json")
        elif "silver" in ds:
            schema_file = os.path.join(base, "silver_schema.json")
        elif "gold" in ds:
            schema_file = os.path.join(base, "gold_schema.json")

        if not schema_file or not os.path.exists(schema_file):
            logger.debug(f"No schema file found for dataset {dataset}, skipping validation")
            return

        with open(schema_file, "r", encoding="utf-8") as f:
            schema = json.load(f)

        required_fields = [f.get("name") for f in schema.get("fields", []) if f.get("mode") == "REQUIRED"]

        missing = [c for c in required_fields if c not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # Try to coerce types for common BigQuery types
        for field in schema.get("fields", []):
            name = field.get("name")
            ftype = field.get("type", "STRING")
            if name not in df.columns:
                continue
            try:
                if ftype in ("TIMESTAMP",):
                    df[name] = pd.to_datetime(df[name], errors="coerce")
                elif ftype in ("DATE",):
                    df[name] = pd.to_datetime(df[name], errors="coerce").dt.date
                elif ftype in ("FLOAT64", "NUMERIC", "FLOAT"):
                    df[name] = pd.to_numeric(df[name], errors="coerce")
                elif ftype in ("INT64", "INTEGER"):
                    df[name] = pd.to_numeric(df[name], errors="coerce").astype("Int64")
                else:
                    # keep as string/object
                    df[name] = df[name].astype(object)
            except Exception as e:
                raise ValueError(f"Failed to coerce column {name} to {ftype}: {e}")

        logger.info(f"Schema validation passed for {dataset}.{table_name}")
