#!/bin/sh
set -eu

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if ! python manage.py shell -c "from apps.catalog.models import Product; raise SystemExit(0 if Product.objects.exists() else 1)"; then
  if [ -f fixtures/store.json ]; then
    python manage.py loaddata fixtures/store.json
  else
    python manage.py seed_store
  fi
fi

exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 2 --timeout 120
