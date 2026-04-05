#!/bin/sh
set -eu

if [ -z "${QB_DATABASE_URL:-}" ]; then
    echo "QB_DATABASE_URL is required" >&2
    exit 1
fi

mkdir -p "${QB_EXPORT_DIR:-/var/lib/qb/exports}"

if [ "${QB_SKIP_MIGRATIONS:-0}" != "1" ]; then
    echo "Waiting for PostgreSQL..."
    until pg_isready -d "$QB_DATABASE_URL" >/dev/null 2>&1; do
        sleep 2
    done

    for migration in /app/migrations/*.sql; do
        if [ ! -f "$migration" ]; then
            continue
        fi
        echo "Applying migration: $(basename "$migration")"
        psql "$QB_DATABASE_URL" -v ON_ERROR_STOP=1 -f "$migration"
    done
fi

exec "$@"
