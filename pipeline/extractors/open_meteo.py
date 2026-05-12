"""Client for Open-Meteo weather API."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class OpenMeteoClient:
    """Client for Open-Meteo Archive API (free, no authentication required)."""

    BASE_URL = "https://archive-api.open-meteo.com/v1/archive"
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(
        self,
        base_url: Optional[str] = None,
        forecast_url: Optional[str] = None,
        timeout: int = 30,
        retries: int = 3,
    ):
        """Initialize Open-Meteo client.

        Args:
            base_url: Base URL for historical data API
            forecast_url: Base URL for forecast API
            timeout: Request timeout in seconds
            retries: Number of retries for failed requests
        """
        self.base_url = base_url or self.BASE_URL
        self.forecast_url = forecast_url or self.FORECAST_URL
        self.timeout = timeout
        self.session = self._create_session(retries)

    def _create_session(self, retries: int) -> requests.Session:
        """Create requests session with retry strategy."""
        session = requests.Session()
        retry_strategy = Retry(
            total=retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            backoff_factor=1,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def get_historical_weather(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
        variables: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Fetch historical weather data for a region.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            variables: Weather variables to retrieve

        Returns:
            JSON response with daily weather data
        """
        if variables is None:
            variables = [
                "temperature_2m_max",
                "temperature_2m_min",
                "temperature_2m_mean",
                "precipitation_sum",
                "relative_humidity_2m_max",
                "relative_humidity_2m_min",
                "relative_humidity_2m_mean",
                "windspeed_10m_max",
                "windspeed_10m_min",
                "windspeed_10m_mean",
                "cloudcover_mean",
            ]

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "daily": ",".join(variables),
            "timezone": "auto",
        }

        try:
            logger.info(
                f"Fetching historical data for lat={latitude}, lon={longitude}, "
                f"period={start_date} to {end_date}"
            )
            response = self.session.get(self.base_url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Successfully fetched {len(data.get('daily', {}).get('time', []))} records")
            return data

        except requests.RequestException as e:
            logger.error(f"Error fetching historical data: {e}")
            raise

    def get_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 7,
        variables: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Fetch weather forecast for next N days.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            days: Number of days to forecast (default 7)
            variables: Weather variables to retrieve

        Returns:
            JSON response with forecast data
        """
        if variables is None:
            variables = [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "cloudcover",
                "windspeed_10m_max",
            ]

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": ",".join(variables),
            "forecast_days": days,
            "timezone": "auto",
        }

        try:
            logger.info(f"Fetching forecast for lat={latitude}, lon={longitude}, days={days}")
            response = self.session.get(self.forecast_url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Successfully fetched forecast with {days} days")
            return data

        except requests.RequestException as e:
            logger.error(f"Error fetching forecast: {e}")
            raise

    def get_last_30_days(
        self, latitude: float, longitude: float, variables: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Convenience method to fetch last 30 days of data."""
        end_date = datetime.now().date().isoformat()
        start_date = (datetime.now().date() - timedelta(days=30)).isoformat()

        return self.get_historical_weather(latitude, longitude, start_date, end_date, variables)
