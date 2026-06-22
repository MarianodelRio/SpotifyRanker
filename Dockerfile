FROM python:3.11-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY apps/ apps/
COPY libs/ libs/
COPY db/ db/

RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -e ".[dev]"

EXPOSE 8000

CMD ["sh", "-c", "python db/init_db.py && exec uvicorn apps.api.main:app --host 0.0.0.0 --port 8000"]
