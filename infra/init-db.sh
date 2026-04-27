#!/bin/bash
set -e

# Create one database per microservice
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE auth_db;
    CREATE DATABASE patient_db;
    CREATE DATABASE practitioner_db;
    CREATE DATABASE appointment_db;
    CREATE DATABASE notification_db;
    CREATE DATABASE analytics_db;
EOSQL
