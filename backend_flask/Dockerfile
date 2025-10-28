FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend_flask/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend_flask/app ./app
COPY backend_flask/main.py .
COPY openapi ./openapi

ARG PORT_BACKEND=3000
ENV PORT_BACKEND=${PORT_BACKEND} \
    FLASK_ENV=production

EXPOSE ${PORT_BACKEND}

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT_BACKEND} main:app"]
