FROM python:3.11-slim

# Set PYTHONPATH so `from src.xxx` imports work without package install
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ── Install dependencies (cached layer) ────────────────────────────────────
RUN pip install --no-cache-dir --upgrade pip

COPY pyproject.toml ./
RUN pip install --no-cache-dir \
        "fastapi>=0.110.0" \
        "uvicorn[standard]>=0.29.0" \
        "pydantic>=2.6.0" \
        "pydantic-settings>=2.2.0" \
        "structlog>=24.1.0" \
        "httpx>=0.27.0" \
        "rq>=1.16.0" \
        "redis>=5.0.0" \
        "sqlalchemy>=2.0.0" \
        "sqlmodel>=0.0.16" \
        "psycopg2-binary>=2.9.9" \
        "alembic>=1.13.0" \
        "pyyaml>=6.0.1" \
        "jinja2>=3.1.3" \
        "python-multipart>=0.0.9" \
        "aiogram>=3.4.0"

# ── Copy application source ────────────────────────────────────────────────
COPY src/ ./src/
COPY config/ ./config/

RUN mkdir -p data

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
