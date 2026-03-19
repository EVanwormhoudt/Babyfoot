#!/usr/bin/env sh
set -eu

if [ ! -f /seed/babyfoot-dump.sql ]; then
  echo "No dump file found at /seed/babyfoot-dump.sql; skipping seed import."
  exit 0
fi

echo "Importing /seed/babyfoot-dump.sql into postgres (owner rewritten to postgres)..."
sed -E 's/OWNER TO [^;]+;/OWNER TO postgres;/g' /seed/babyfoot-dump.sql \
  | psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres
echo "Seed import complete."
