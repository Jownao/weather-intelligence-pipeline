"""Unit tests for WeatherTransformer."""

import pytest
import pandas as pd
from datetime import datetime

from pipeline.transformers.weather_transformer import WeatherTransformer


@pytest.fixture
def mock_api_response():
    """Mock Open-Meteo API response."""
    return {
        "latitude": -23.5505,
        "longitude": -46.6333,
        "daily": {
            "time": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "temperature_2m_mean": [25.0, 26.0, 24.5],
            "temperature_2m_max": [30.0, 31.0, 29.5],
            "temperature_2m_min": [20.0, 21.0, 19.5],
            "precipitation_sum": [0.0, 5.2, 0.0],
            "relative_humidity_2m_mean": [70, 75, 68],
            "windspeed_10m_mean": [10.0, 12.0, 9.5],
            "cloudcover_mean": [20, 50, 10],
        },
    }


def test_transform_open_meteo_response(mock_api_response):
    """Test transformation of API response to DataFrame."""
    df = WeatherTransformer.transform_open_meteo_response(
        api_response=mock_api_response,
        region_name="São Paulo",
        region_code="SP",
        extraction_timestamp=datetime.utcnow(),
    )

    assert len(df) == 3
    assert "region_name" in df.columns
    assert df["region_name"].iloc[0] == "São Paulo"
    assert df["region_code"].iloc[0] == "SP"
    assert df["latitude"].iloc[0] == -23.5505


def test_clean_weather_data(mock_api_response):
    """Test data cleaning and quality scoring."""
    df = WeatherTransformer.transform_open_meteo_response(
        api_response=mock_api_response,
        region_name="São Paulo",
        region_code="SP",
        extraction_timestamp=datetime.utcnow(),
    )

    df_clean, metrics = WeatherTransformer.clean_weather_data(df)

    assert "data_quality_score" in df_clean.columns
    assert "is_valid" in df_clean.columns
    assert metrics["initial_rows"] == 3
    assert (df_clean["data_quality_score"] >= 0).all()
    assert (df_clean["data_quality_score"] <= 100).all()


def test_remove_outliers():
    """Test outlier removal."""
    data = {
        "temperature_2m": [-100, 25.0, 26.0, 80],
        "precipitation_sum": [-1, 0.0, 5.2, 0.0],
        "relative_humidity_2m": [70, 75, 120, 68],
    }
    df = pd.DataFrame(data)

    df_clean = WeatherTransformer._remove_outliers(df)

    assert len(df_clean) < len(df)
    assert (df_clean["temperature_2m"] >= -50).all()
    assert (df_clean["temperature_2m"] <= 60).all()
    assert (df_clean["precipitation_sum"] >= 0).all()
    assert (df_clean["relative_humidity_2m"] >= 0).all()
    assert (df_clean["relative_humidity_2m"] <= 100).all()


def test_categorize_weather_condition():
    """Test weather condition categorization."""
    row = pd.Series({"precipitation_sum": 0, "cloudcover": 10})
    assert WeatherTransformer.categorize_weather_condition(row) == "sunny"

    row = pd.Series({"precipitation_sum": 0, "cloudcover": 60})
    assert WeatherTransformer.categorize_weather_condition(row) == "partly_cloudy"

    row = pd.Series({"precipitation_sum": 5, "cloudcover": 80})
    assert WeatherTransformer.categorize_weather_condition(row) == "rainy"

    row = pd.Series({"precipitation_sum": 15, "cloudcover": 100})
    assert WeatherTransformer.categorize_weather_condition(row) == "very_rainy"
