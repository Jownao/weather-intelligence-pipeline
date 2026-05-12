-- Silver Layer Transformation
-- Cleans and standardizes Bronze raw data
-- Run daily after Bronze loading

CREATE OR REPLACE TABLE `{PROJECT_ID}.weather_silver.weather_cleaned` AS
SELECT
  -- Identifiers
  GENERATE_UUID() as weather_id,
  region_name,
  region_code,
  CAST(date AS DATE) as date,

  -- Temperature
  CAST(temperature_2m AS FLOAT64) as temperature_celsius,
  CAST(temperature_max AS FLOAT64) as temperature_max_celsius,
  CAST(temperature_min AS FLOAT64) as temperature_min_celsius,

  -- Humidity & Precipitation
  CAST(relative_humidity_2m AS FLOAT64) as humidity_percentage,
  CAST(precipitation_sum AS FLOAT64) as precipitation_mm,

  -- Wind
  CAST(windspeed_10m AS FLOAT64) as wind_speed_kmh,

  -- Cloud & Quality
  CAST(cloudcover AS INT64) as cloud_coverage_percentage,

  -- Categorization
  CASE
    WHEN CAST(precipitation_sum AS FLOAT64) > 10 THEN 'very_rainy'
    WHEN CAST(precipitation_sum AS FLOAT64) > 2 THEN 'rainy'
    WHEN CAST(cloudcover AS INT64) > 80 THEN 'cloudy'
    WHEN CAST(cloudcover AS INT64) > 30 THEN 'partly_cloudy'
    ELSE 'sunny'
  END as weather_condition,

  -- Quality metrics
  100.0 as data_quality_score,
  TRUE as is_valid,

  -- Timestamps
  CURRENT_TIMESTAMP() as transformation_timestamp

FROM `{PROJECT_ID}.weather_bronze.weather_raw`
WHERE
  date IS NOT NULL
  AND temperature_2m IS NOT NULL
  AND extraction_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 2 DAY)
