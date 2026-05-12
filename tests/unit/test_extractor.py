"""Unit tests for OpenMeteoClient."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from pipeline.extractors.open_meteo import OpenMeteoClient


@pytest.fixture
def client():
    """Create OpenMeteoClient for testing."""
    return OpenMeteoClient(retries=1)


@pytest.fixture
def mock_response():
    """Mock API response from Open-Meteo."""
    return {
        "latitude": -23.5505,
        "longitude": -46.6333,
        "timezone": "America/Sao_Paulo",
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


def test_client_initialization(client):
    """Test OpenMeteoClient initialization."""
    assert client.base_url == "https://archive-api.open-meteo.com/v1/archive"
    assert client.timeout == 30
    assert client.session is not None


@patch("pipeline.extractors.open_meteo.requests.Session.get")
def test_get_historical_weather(mock_get, client, mock_response):
    """Test fetching historical weather data."""
    mock_get.return_value.json.return_value = mock_response
    mock_get.return_value.raise_for_status.return_value = None

    result = client.get_historical_weather(
        latitude=-23.5505,
        longitude=-46.6333,
        start_date="2024-01-01",
        end_date="2024-01-03",
    )

    assert result == mock_response
    assert len(result["daily"]["time"]) == 3
    assert result["latitude"] == -23.5505


@patch("pipeline.extractors.open_meteo.requests.Session.get")
def test_get_forecast(mock_get, client, mock_response):
    """Test fetching forecast data."""
    mock_get.return_value.json.return_value = mock_response
    mock_get.return_value.raise_for_status.return_value = None

    result = client.get_forecast(
        latitude=-23.5505,
        longitude=-46.6333,
        days=7,
    )

    assert result == mock_response
    mock_get.assert_called_once()


@patch("pipeline.extractors.open_meteo.requests.Session.get")
def test_api_error_handling(mock_get, client):
    """Test error handling for API failures."""
    mock_get.return_value.raise_for_status.side_effect = Exception("API Error")

    with pytest.raises(Exception):
        client.get_historical_weather(
            latitude=-23.5505,
            longitude=-46.6333,
            start_date="2024-01-01",
            end_date="2024-01-03",
        )
