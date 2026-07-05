FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/usr/local

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl build-essential \
    && rm -rf /var/lib/apt/lists/*

# kubectl — the infra agent reaches its target cluster and validates the CRD through it.
RUN curl -fsSLo /usr/local/bin/kubectl \
        "https://dl.k8s.io/release/$(curl -fsSL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x /usr/local/bin/kubectl

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Deps layer — cached unless pyproject/uv.lock change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Source is bind-mounted in compose for hot reload; this COPY is only a
# fallback so `docker build` alone produces a runnable image.
COPY . .

EXPOSE 8000
CMD ["uvicorn", "ui.backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
