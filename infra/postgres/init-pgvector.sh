#!/usr/bin/env sh
# init-pgvector.sh — install pgvector extension в dev Postgres
#
# Postgres docker image автоматически выполняет всё в /docker-entrypoint-initdb.d/
# на первом старте (когда volume пустой). Этот скрипт устанавливает pgvector
# extension required по ADR-001 + ADR-024.
#
# Note: используется образ `pgvector/pgvector:pg16` (официальный Postgres 16 с
# preinstalled pgvector). Этот скрипт делает только `CREATE EXTENSION` в DB.

set -eu

echo "→ Installing pgvector extension in database ${POSTGRES_DB}..."

psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" --dbname "${POSTGRES_DB}" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE EXTENSION IF NOT EXISTS pg_trgm;
    CREATE EXTENSION IF NOT EXISTS unaccent;
EOSQL

echo "✓ pgvector + pg_trgm + unaccent extensions installed in ${POSTGRES_DB}"
