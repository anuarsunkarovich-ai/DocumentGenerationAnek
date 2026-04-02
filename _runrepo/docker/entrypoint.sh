#!/bin/sh
set -eu

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  uv run alembic upgrade head
fi

exec "$@"
