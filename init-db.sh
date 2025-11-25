# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE fastapi_test_db;
EOSQL
