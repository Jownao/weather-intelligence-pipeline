-- Gold Layer Aggregations
-- Creates analytics-ready aggregates by region and SaaS vertical
-- Supports delivery, fitness, and agronegócio use cases

CREATE OR REPLACE TABLE `{PROJECT_ID}.weather_gold.weather_aggregates` AS
SELECT
  -- Dimensions
  wc.date as metric_date,
  wc.region_name,
  wc.region_code,
  'delivery' as saas_vertical,  -- Parameterize this for different verticals

  -- Temperature metrics
  ROUND(AVG(wc.temperature_celsius), 2) as avg_temperature_celsius,
  ROUND(MIN(wc.temperature_celsius), 2) as min_temperature_celsius,
  ROUND(MAX(wc.temperature_celsius), 2) as max_temperature_celsius,

  -- Precipitation
  ROUND(SUM(wc.precipitation_mm), 2) as total_precipitation_mm,

  -- Humidity
  ROUND(AVG(wc.humidity_percentage), 2) as avg_humidity_percentage,

  -- Wind
  ROUND(AVG(wc.wind_speed_kmh), 2) as avg_wind_speed_kmh,

  -- Cloud
  ROUND(AVG(wc.cloud_coverage_percentage), 0) as avg_cloud_coverage_percentage,

  -- Business metrics
  COUNTIF(wc.precipitation_mm > 1) as rainy_days,
  COUNTIF(wc.temperature_celsius > 30 OR wc.temperature_celsius < 15) as extreme_temperature_days,

  -- Timestamp
  CURRENT_TIMESTAMP() as aggregation_timestamp

FROM `{PROJECT_ID}.weather_silver.weather_cleaned` wc
WHERE
  wc.is_valid = TRUE
GROUP BY
  wc.date,
  wc.region_name,
  wc.region_code
ORDER BY
  wc.date DESC,
  wc.region_name
