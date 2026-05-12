"""Generate mock weather data for testing without API calls."""

import json
import logging
from datetime import datetime, timedelta

import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_mock_open_meteo_response(days: int = 30) -> dict:
    """Generate mock Open-Meteo API response for testing.

    Args:
        days: Number of days of data to generate

    Returns:
        Dict matching Open-Meteo API response format
    """
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    dates = []
    temps = []
    humidity = []
    precipitation = []
    wind_speed = []
    cloud_cover = []

    current = start_date
    while current <= end_date:
        dates.append(current.isoformat())

        # Generate realistic Brazilian weather
        # São Paulo: 10-30°C, varies seasonally
        base_temp = 20 + (current.month - 6) * 1.5
        temps.append(base_temp + (hash(current.isoformat()) % 10 - 5) / 2)

        # Humidity: 50-90%
        humidity.append(70 + (hash(current.isoformat()) % 20 - 10))

        # Precipitation: mostly 0, occasional rain
        precip_chance = 0.3 if current.month in [12, 1, 2] else 0.15  # Summer rainy season
        precipitation.append(
            (hash(current.isoformat()) % 100) * 0.05 if hash(current.isoformat()) % 10 < 3 else 0
        )

        # Wind speed: 5-20 km/h
        wind_speed.append(10 + (hash(current.isoformat()) % 10))

        # Cloud cover: 0-100%
        cloud_cover.append(hash(current.isoformat()) % 100)

        current += timedelta(days=1)

    return {
        "latitude": -23.5505,
        "longitude": -46.6333,
        "timezone": "America/Sao_Paulo",
        "daily": {
            "time": dates,
            "temperature_2m_mean": temps,
            "temperature_2m_max": [t + 5 for t in temps],
            "temperature_2m_min": [t - 3 for t in temps],
            "relative_humidity_2m_mean": humidity,
            "precipitation_sum": precipitation,
            "windspeed_10m_mean": wind_speed,
            "cloudcover_mean": cloud_cover,
        },
    }


def save_mock_data(output_path: str = "mock_weather_data.json") -> None:
    """Generate and save mock weather data to JSON file.

    Args:
        output_path: Path to save JSON file
    """
    data = generate_mock_open_meteo_response(days=30)

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    logger.info(f"✅ Mock data saved to {output_path}")
    logger.info(f"   Generated {len(data['daily']['time'])} days of weather data")


if __name__ == "__main__":
    save_mock_data()
