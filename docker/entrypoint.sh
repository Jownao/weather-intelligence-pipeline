#!/bin/bash

set -e

echo "🚀 Starting Airflow initialization..."

# Initialize database
airflow db upgrade

# Create default admin user if not exists
airflow users create \
    --username admin \
    --password admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@weather-saas.local \
    || echo "Admin user already exists"

echo "✅ Database initialized"

# Execute command passed as argument
exec "$@"
