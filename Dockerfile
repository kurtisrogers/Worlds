FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings \
    AI_ASSIST_ENABLED=false

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY manage.py .
COPY config ./config
COPY accounts ./accounts
COPY editor ./editor
COPY integrations ./integrations
COPY library ./library
COPY payments ./payments
COPY stories ./stories
COPY templates ./templates
COPY static ./static
COPY docker/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
