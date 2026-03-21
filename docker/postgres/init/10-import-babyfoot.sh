#!/usr/bin/env sh
set -eu

if [ ! -s /seed/babyfoot.sql ]; then
  echo "ERROR: expected /seed/babyfoot.sql to exist and be non-empty, but it was not found."
  echo "       In Portainer, make sure the stack deploy includes babyfoot.sql at the compose path."
  exit 1
fi

echo "Importing /seed/babyfoot.sql into ${POSTGRES_DB}..."
sed -E 's/OWNER TO [^;]+;/OWNER TO postgres;/g' /seed/babyfoot.sql \
  | psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"
echo "Seed import complete."
