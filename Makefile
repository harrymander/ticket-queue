BACKEND_DEV_HOST ?= localhost
BACKEND_DEV_PORT ?= 8889
FRONTEND_DEV_HOST ?= localhost
FRONTEND_DEV_PORT ?= 7777
DEV_DB_PATH ?= .queue.dev.db
DEV_ADMIN_PASSWORD ?= admin


.PHONY: help
help:
	@echo "dev-backend   Run backend dev server"
	@echo "dev-frontend  Run frontend dev server"
	@echo "help          Show this help"


.PHONY: dev-backend
dev-backend:
	uv run --locked ticket-queue \
		--host '$(BACKEND_DEV_HOST)' \
		--port $(BACKEND_DEV_PORT) \
		--reload \
		--url 'http://$(FRONTEND_DEV_HOST):$(FRONTEND_DEV_PORT)' \
		--no-frontend \
		--database '$(DEV_DB_PATH)' \
		--admin-password $(DEV_ADMIN_PASSWORD)


.PHONY: dev-frontend
dev-frontend:
	cd frontend && \
	VITE_BACKEND_URL='http://$(BACKEND_DEV_HOST):$(BACKEND_DEV_PORT)/api' \
	npm run dev -- \
	--host '$(FRONTEND_DEV_HOST)' \
	--port $(FRONTEND_DEV_PORT)
