BACKEND_HOST ?= localhost
BACKEND_PORT ?= 8889
FRONTEND_DEV_HOST ?= localhost
FRONTEND_DEV_PORT ?= 7777
DEV_DB_PATH ?= .queue.dev.db
DEV_ADMIN_PASSWORD ?= admin


.PHONY: all
all: help
	@echo "Error: a target is required!"
	@false


.PHONY: help
help:
	@echo "The following targets are available:"
	@echo "  dev-backend           Run backend dev server"
	@echo "  dev-frontend          Run frontend dev server"
	@echo "  dev-backend-frontend  Build frontend and run backend dev server that serves"
	@echo "                        the frontend"
	@echo "  frontend              Build the frontend"
	@echo "  preview               Build frontend and run server in production mode"
	@echo "  preview               Build frontend and run server in production mode"
	@echo "  clean                 Clean frontend build outputs and dev server artifacts"
	@echo "  help                  Show this help"


RUN_BACKEND = uv run --locked ticket-queue \
	--host '$(BACKEND_HOST)' \
	--port $(BACKEND_PORT)

RUN_BACKEND_DEV = $(RUN_BACKEND) \
	--reload \
	--database '$(DEV_DB_PATH)' \
	--admin-password $(DEV_ADMIN_PASSWORD)


.PHONY: dev-backend
dev-backend:
	$(RUN_BACKEND_DEV) \
	--frontend 'http://$(FRONTEND_DEV_HOST):$(FRONTEND_DEV_PORT)'


FRONTEND_BUILD_DIR = frontend/dist

.PHONY: dev-backend-frontend
dev-backend-frontend: frontend
	$(RUN_BACKEND_DEV) --frontend $(FRONTEND_BUILD_DIR)


.PHONY: preview
preview: frontend
	$(RUN_BACKEND) --frontend $(FRONTEND_BUILD_DIR)


.PHONY: dev-frontend
dev-frontend:
	cd frontend && \
	VITE_BACKEND_URL='http://$(BACKEND_HOST):$(BACKEND_PORT)/api' \
	npm run dev -- \
	--host '$(FRONTEND_DEV_HOST)' \
	--port $(FRONTEND_DEV_PORT)


.PHONY: frontend
frontend:
	cd frontend && npm run build


.PHONY: clean
clean:
	rm -rf $(FRONTEND_BUILD_DIR) $(DEV_DB_PATH)
