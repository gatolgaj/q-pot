# ──────────────────────────────────────────────────────────────
# FinCoach – all-in-one container
# ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

# Nice defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System libs (if cryptography or other wheels need build tools)
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends build-essential ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy source AFTER installing deps → better cache
COPY . .

# Port FastAPI listens on
EXPOSE 8000

CMD ["uvicorn", "chat_web.app:app", "--host", "0.0.0.0", "--port", "8000"] 