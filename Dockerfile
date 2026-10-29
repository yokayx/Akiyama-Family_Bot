# --- Фронтенд: Vite + React (сборка в image) ---
FROM node:22-alpine AS fe
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Бот + сайт (FastAPI serves SPA + API) ---
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN useradd --create-home --uid 1000 akiyama \
    && mkdir -p /app/data

COPY pyproject.toml README.md ./
COPY bot ./bot
COPY --from=fe /fe/dist /app/frontend/dist

RUN pip install --no-cache-dir . \
    && chown -R akiyama:akiyama /app

USER akiyama

VOLUME ["/app/data"]

CMD ["python", "-m", "bot"]
