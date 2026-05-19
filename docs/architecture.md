# Architecture Overview

This document summarizes the architecture of the Weather Intelligence Pipeline.

Components
- Source: Open-Meteo API (historical and forecast)
- Orchestration: Apache Airflow (DAGs in `dags/`)
- Processing: Python + pandas (transformers in `pipeline/transformers`)
- Storage: Google BigQuery (Bronze / Silver / Gold datasets)
- Dev environment: Docker Compose (Airflow, Postgres)

Data Flow
1. Airflow triggers the ETL DAG on a schedule.
2. Extractor queries Open-Meteo and writes raw payloads into the Bronze table.
3. Transformer normalizes fields, computes quality metrics and writes to Silver.
4. Aggregations are materialized into Gold for BI and analytics.

Security & Secrets
- Use environment variables for local development (`.env`).
- For production, move service account keys into a secret manager (GCP Secret Manager) and use workload identity.

Monitoring
- Airflow UI for DAG status, retries and logs.
- BigQuery cost & quota alerts in GCP.
