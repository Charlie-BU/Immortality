#!/bin/sh
set -eu

DB_EXISTS="$(psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT 1 FROM pg_database WHERE datname = 'immortality_checkpoint';" | tr -d '[:space:]')"
if [ "$DB_EXISTS" != "1" ]; then
  psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE DATABASE immortality_checkpoint;"
fi

# Ensure pgvector extension exists in both main and checkpoint databases.
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "immortality_checkpoint" -c "CREATE EXTENSION IF NOT EXISTS vector;"
