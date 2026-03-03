#!/bin/sh
set -eu

if [ -z "${RESTORE_FILE:-}" ]; then
  echo "RESTORE_FILE is required, for example RESTORE_FILE=mydump.dump"
  exit 1
fi

FILE="/backups/${RESTORE_FILE}"

if [ ! -f "$FILE" ]; then
  echo "Restore file not found: $FILE"
  exit 1
fi

echo "Restoring $FILE into ${POSTGRES_DB} on db:5432"

case "$FILE" in
  *.dump|*.backup|*.tar)
    pg_restore \
      --host=db \
      --port=5432 \
      --username="${POSTGRES_USER}" \
      --dbname="${POSTGRES_DB}" \
      --clean \
      --if-exists \
      --no-owner \
      --no-privileges \
      "$FILE"
    ;;
  *.sql)
    psql \
      --host=db \
      --port=5432 \
      --username="${POSTGRES_USER}" \
      --dbname="${POSTGRES_DB}" \
      --set=ON_ERROR_STOP=1 \
      --file="$FILE"
    ;;
  *)
    echo "Unsupported restore file type: $FILE"
    echo "Use .dump, .backup, .tar, or .sql"
    exit 1
    ;;
esac

echo "Restore complete"
