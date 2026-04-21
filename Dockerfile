FROM node:25-alpine3.22 AS frontend

COPY frontend /frontend
WORKDIR /frontend
RUN npm ci
RUN npm run build

FROM python:3.13-alpine

COPY --from=frontend /frontend/dist /app/frontend
COPY ticket_queue /app/ticket_queue
COPY pyproject.toml uv.lock frontend_build_hook.py /app/

WORKDIR /app
ENV TICKET_QUEUE_DISABLE_FRONTEND_BUILD=1
RUN --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    uv sync --locked --no-cache --no-dev

ENTRYPOINT ["/app/.venv/bin/ticket-queue", "--no-browser", "--frontend=/app/frontend"]
