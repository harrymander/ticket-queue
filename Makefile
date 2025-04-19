BACKEND_HOST ?= localhost
BACKEND_PORT ?= 8889
FRONTEND_DEV_HOST ?= localhost
FRONTEND_DEV_PORT ?= 7777
DEV_ADMIN_PASSWORD ?= admin
BACKEND_PREVIEW_WORKERS ?= 1


.PHONY: all
all: help
	@echo "Error: a target is required!"
	@false


.PHONY: help
help:
	@echo "The following targets are available:"
	@echo "  dev                   Run backend/frontend dev servers (requires tmux)"
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

ifneq ($(DEV_DB_PATH),)
	DEV_DB_ARG = --database '$(DEV_DB_PATH)'
endif
RUN_BACKEND_DEV = $(RUN_BACKEND) \
	--reload \
	$(DEV_DB_ARG) \
	--admin-password '$(DEV_ADMIN_PASSWORD)'


.PHONY: dev
dev:
	tmux \
		new-session "$(MAKE) dev-backend || read" ";" \
		split-window -h "$(MAKE) dev-frontend || read"

.PHONY: dev-backend
dev-backend:
	$(RUN_BACKEND_DEV) \
	--frontend 'http://$(FRONTEND_DEV_HOST):$(FRONTEND_DEV_PORT)' \
	$(BACKEND_EXTRA_ARGS)


FRONTEND_BUILD_DIR = frontend/dist

.PHONY: dev-backend-frontend
dev-backend-frontend: frontend
	$(RUN_BACKEND_DEV) \
	--frontend $(FRONTEND_BUILD_DIR) \
	$(BACKEND_EXTRA_ARGS)


.PHONY: preview
preview: frontend
	$(RUN_BACKEND) \
	--workers $(BACKEND_PREVIEW_WORKERS) \
	--frontend $(FRONTEND_BUILD_DIR) \
	$(BACKEND_EXTRA_ARGS)


.PHONY: dev-frontend
dev-frontend:
	cd frontend && \
	VITE_BACKEND_URL='http://$(BACKEND_HOST):$(BACKEND_PORT)/api' \
	npm run dev -- \
	--host '$(FRONTEND_DEV_HOST)' \
	--port $(FRONTEND_DEV_PORT) \
	$(FRONTEND_EXTRA_ARGS)


.PHONY: frontend
frontend:
	cd frontend && npm run build


.PHONY: clean
clean:
	rm -rf $(FRONTEND_BUILD_DIR) $(DEV_DB_PATH)
