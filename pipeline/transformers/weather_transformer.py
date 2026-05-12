"""Weather data transformation and cleaning logic."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class WeatherTransformer:
    """Transform raw weather API responses into cleaned, standardized data."""

    @staticmethod
    def transform_open_meteo_response(
        api_response: Dict[str, Any],
        region_name: str,
        region_code: str,
        extraction_timestamp: datetime,
    ) -> pd.DataFrame:
        """Transform Open-Meteo API response to DataFrame.

        Args:
            api_response: Raw API response from Open-Meteo
            region_name: Name of the region
            region_code: Region code (state abbreviation)
            extraction_timestamp: When data was extracted

        Returns:
            Cleaned DataFrame ready for loading
        """
        try:
            # Extract coordinates and daily data
            latitude = api_response.get("latitude")
            longitude = api_response.get("longitude")
            daily = api_response.get("daily", {})

            if not daily or not daily.get("time"):
                logger.warning(f"No daily data found for {region_name}")
                return pd.DataFrame()

            # Create base dataframe from dates
            df = pd.DataFrame({"date": daily.get("time", [])})
            df["date"] = pd.to_datetime(df["date"]).dt.date

            # Map API field names to standardized names
            field_mapping = {
                "temperature_2m_mean": "temperature_2m",
                "temperature_2m_max": "temperature_max",
                "temperature_2m_min": "temperature_min",
                "relative_humidity_2m_mean": "relative_humidity_2m",
                "precipitation_sum": "precipitation_sum",
                "windspeed_10m_mean": "windspeed_10m",
                "cloudcover_mean": "cloudcover",
            }

            # Add available fields
            for api_field, standard_field in field_mapping.items():
                if api_field in daily:
                    df[standard_field] = daily[api_field]

            # Add region and metadata
            df["region_name"] = region_name
            df["region_code"] = region_code
            df["latitude"] = latitude
            df["longitude"] = longitude
            df["extraction_timestamp"] = extraction_timestamp
            df["load_timestamp"] = datetime.utcnow()

            logger.info(f"Transformed {len(df)} records for {region_name}")
            return df

        except Exception as e:
            logger.error(f"Error transforming data for {region_name}: {e}")
            raise

    @staticmethod
    def clean_weather_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
        """Clean and validate weather data.

        Args:
            df: Raw transformed dataframe

        Returns:
            Cleaned dataframe and quality metrics dict
        """
        initial_rows = len(df)
        quality_metrics = {"initial_rows": initial_rows}

        if df.empty:
            return df, quality_metrics

        # Handle missing values
        # Temperature: interpolate if few missing, drop row if many
        if "temperature_2m" in df.columns:
            missing_temp = df["temperature_2m"].isna().sum()
            if missing_temp / len(df) < 0.2:  # Less than 20% missing
                df["temperature_2m"] = df["temperature_2m"].interpolate(method="linear")
            else:
                df = df.dropna(subset=["temperature_2m"])

        # Precipitation: fill 0 if missing (reasonable assumption)
        if "precipitation_sum" in df.columns:
            df["precipitation_sum"] = df["precipitation_sum"].fillna(0)

        # Humidity and wind: interpolate
        for col in ["relative_humidity_2m", "windspeed_10m", "cloudcover"]:
            if col in df.columns:
                df[col] = df[col].interpolate(method="linear")

        # Remove outliers (unreasonable values)
        df = WeatherTransformer._remove_outliers(df)

        # Add data quality score
        df["data_quality_score"] = WeatherTransformer._calculate_quality_score(df)
        df["is_valid"] = df["data_quality_score"] >= 70

        quality_metrics["final_rows"] = len(df)
        quality_metrics["rows_removed"] = initial_rows - len(df)
        quality_metrics["invalid_rows"] = (~df["is_valid"]).sum()

        logger.info(f"Data quality metrics: {quality_metrics}")
        return df, quality_metrics

    @staticmethod
    def _remove_outliers(df: pd.DataFrame) -> pd.DataFrame:
        """Remove unreasonable temperature and precipitation values."""
        # Temperature range: -50°C to 60°C (extreme but possible)
        if "temperature_2m" in df.columns:
            df = df[(df["temperature_2m"] >= -50) & (df["temperature_2m"] <= 60)]

        # Precipitation: negative values impossible
        if "precipitation_sum" in df.columns:
            df = df[df["precipitation_sum"] >= 0]

        # Humidity: must be 0-100
        if "relative_humidity_2m" in df.columns:
            df = df[(df["relative_humidity_2m"] >= 0) & (df["relative_humidity_2m"] <= 100)]

        return df

    @staticmethod
    def _calculate_quality_score(df: pd.DataFrame) -> pd.Series:
        """Calculate quality score for each row (0-100)."""
        score = pd.Series(100, index=df.index)

        # Deduct points for missing values
        for col in df.columns:
            if df[col].isna().any():
                score -= 10

        # Deduct points for outliers
        if "temperature_2m" in df.columns:
            extreme_temp = (df["temperature_2m"] < -30) | (df["temperature_2m"] > 50)
            score[extreme_temp] -= 20

        return score.clip(lower=0, upper=100)

    @staticmethod
    def categorize_weather_condition(row: pd.Series) -> str:
        """Categorize weather based on precipitation and cloud cover."""
        precip = row.get("precipitation_sum", 0) or 0
        cloud = row.get("cloudcover", 0) or 0

        if precip > 10:
            return "very_rainy"
        elif precip > 2:
            return "rainy"
        elif cloud > 80:
            return "cloudy"
        elif cloud > 30:
            return "partly_cloudy"
        else:
            return "sunny"
