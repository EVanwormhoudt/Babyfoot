#!/usr/bin/env sh
set -eu

if [ ! -f /seed/babyfoot.sql ]; then
  echo "No dump file found at /seed/babyfoot.sql; skipping seed import."
  exit 0
fi

echo "Importing /seed/babyfoot.sql into ${POSTGRES_DB}..."
sed -E 's/OWNER TO [^;]+;/OWNER TO postgres;/g' /seed/babyfoot.sql \
  | psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"
echo "Seed import complete."
