import pandas as pd
import os
from pipeline.loaders.bigquery_loader import BigQueryLoader


def test_validate_schema_missing_column_raises():
    loader = BigQueryLoader(project_id="test-project")
    # create df missing a required column from bronze schema
    df = pd.DataFrame({
        "extraction_timestamp": [pd.Timestamp.now()],
        # 'region_name' is missing intentionally
        "latitude": [10.0],
        "longitude": [20.0],
        "date": [pd.Timestamp.today().date()],
        "load_timestamp": [pd.Timestamp.now()],
    })

    try:
        loader.validate_df_schema(df, "weather_bronze", "weather_raw")
        assert False, "Expected ValueError for missing required columns"
    except ValueError as e:
        assert "Missing required columns" in str(e)


def test_validate_schema_passes_with_required_columns():
    loader = BigQueryLoader(project_id="test-project")
    df = pd.DataFrame({
        "extraction_timestamp": [pd.Timestamp.now()],
        "region_name": ["Test Region"],
        "latitude": [10.0],
        "longitude": [20.0],
        "date": [pd.Timestamp.today().date()],
        "load_timestamp": [pd.Timestamp.now()],
    })

    # should not raise
    loader.validate_df_schema(df, "weather_bronze", "weather_raw")
