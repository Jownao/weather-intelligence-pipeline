"""Data quality validation using Great Expectations and custom checks."""

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class DataQualityValidator:
    """Validate weather data quality using custom rules and Great Expectations."""

    def __init__(self, min_quality_score: float = 70.0):
        """Initialize validator.

        Args:
            min_quality_score: Minimum acceptable data quality score
        """
        self.min_quality_score = min_quality_score

    def validate_raw_data(self, df: pd.DataFrame, region: str) -> Dict[str, Any]:
        """Validate raw extracted data.

        Args:
            df: Raw DataFrame
            region: Region name for logging

        Returns:
            Validation report dict
        """
        report = {
            "region": region,
            "valid": True,
            "checks": {},
            "warnings": [],
            "errors": [],
        }

        # Check 1: Not empty
        if df.empty:
            report["valid"] = False
            report["errors"].append("DataFrame is empty")
            return report

        report["checks"]["row_count"] = len(df)

        # Check 2: Required columns exist
        required_cols = ["date", "temperature_2m", "precipitation_sum"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            report["valid"] = False
            report["errors"].append(f"Missing columns: {missing_cols}")

        # Check 3: Date range is reasonable
        if "date" in df.columns:
            try:
                date_range = pd.to_datetime(df["date"]).max() - pd.to_datetime(df["date"]).min()
                report["checks"]["date_range_days"] = date_range.days
            except Exception as e:
                report["warnings"].append(f"Could not parse dates: {e}")

        # Check 4: Nulls percentage
        for col in df.columns:
            null_pct = (df[col].isna().sum() / len(df)) * 100
            if null_pct > 50:
                report["warnings"].append(f"Column {col} has {null_pct:.1f}% nulls")

        # Check 5: Numeric ranges
        if "temperature_2m" in df.columns:
            temp_min = df["temperature_2m"].min()
            temp_max = df["temperature_2m"].max()
            report["checks"]["temperature_range"] = {"min": temp_min, "max": temp_max}

            if temp_min < -60 or temp_max > 70:
                report["warnings"].append(
                    f"Extreme temperature values detected: {temp_min} to {temp_max}°C"
                )

        logger.info(f"Raw data validation for {region}: valid={report['valid']}")
        return report

    def validate_cleaned_data(self, df: pd.DataFrame, region: str) -> Dict[str, Any]:
        """Validate cleaned data before loading to Silver.

        Args:
            df: Cleaned DataFrame
            region: Region name for logging

        Returns:
            Validation report dict
        """
        report = {
            "region": region,
            "valid": True,
            "checks": {},
            "warnings": [],
            "errors": [],
        }

        if df.empty:
            report["valid"] = False
            report["errors"].append("Cleaned DataFrame is empty")
            return report

        # Check data quality scores
        if "data_quality_score" in df.columns:
            avg_score = df["data_quality_score"].mean()
            report["checks"]["avg_quality_score"] = avg_score

            if avg_score < self.min_quality_score:
                report["valid"] = False
                report["errors"].append(f"Average quality score {avg_score:.1f} below minimum")

            invalid_count = (~df["is_valid"]).sum()
            if invalid_count > 0:
                report["warnings"].append(f"{invalid_count} invalid records detected")

        # Check for nulls in key columns
        key_cols = ["temperature_2m", "precipitation_sum", "relative_humidity_2m"]
        for col in key_cols:
            if col in df.columns:
                null_count = df[col].isna().sum()
                if null_count > 0:
                    report["errors"].append(f"Column {col} contains {null_count} nulls")

        # Check date coverage
        if "date" in df.columns:
            date_count = df["date"].nunique()
            report["checks"]["unique_dates"] = date_count

        logger.info(f"Cleaned data validation for {region}: valid={report['valid']}")
        return report

    @staticmethod
    def generate_validation_report(validations: List[Dict[str, Any]]) -> None:
        """Print summary validation report.

        Args:
            validations: List of validation report dicts
        """
        total = len(validations)
        valid = sum(1 for v in validations if v["valid"])
        invalid = total - valid

        logger.info("=" * 60)
        logger.info("DATA QUALITY VALIDATION REPORT")
        logger.info("=" * 60)
        logger.info(f"Total regions validated: {total}")
        logger.info(f"Valid: {valid} ({(valid/total)*100:.1f}%)")
        logger.info(f"Invalid: {invalid} ({(invalid/total)*100:.1f}%)")

        if invalid > 0:
            logger.warning("\nFailed validations:")
            for v in validations:
                if not v["valid"]:
                    logger.warning(f"  - {v['region']}: {v['errors']}")
