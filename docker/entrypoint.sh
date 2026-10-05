#!/bin/sh
set -eu

python manage.py migrate --settings=config.settings
python manage.py collectstatic --noinput --settings=config.settings
exec python manage.py runserver 0.0.0.0:8000 --settings=config.settings
