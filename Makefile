# ============================================================================
# SparqAI — Development & Operations Makefile
# ============================================================================

.PHONY: help dev dev-backend dev-frontend build test deploy logs db-migrate \
        staging lint lint-backend lint-frontend health clean docker-clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Local Development
# ---------------------------------------------------------------------------

dev: ## Start full stack locally with docker-compose
	docker compose up --build

dev-backend: ## Start backend only (for local dev)
	cd backend && DATABASE_URL=sqlite:///./test.db uvicorn app.main:app --reload --port 8000

dev-frontend: ## Start frontend only (for local dev)
	cd frontend && NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1 npm run dev

install: ## Install all dependencies
	cd backend && pip install -r requirements.txt
	cd frontend && npm ci

# ---------------------------------------------------------------------------
# Staging
# ---------------------------------------------------------------------------

staging: ## Start staging environment with docker-compose
	docker compose -f docker-compose.staging.yml up --build

staging-down: ## Stop staging environment and remove volumes
	docker compose -f docker-compose.staging.yml down -v

staging-logs: ## Tail staging backend logs
	docker compose -f docker-compose.staging.yml logs -f backend

# ---------------------------------------------------------------------------
# Build & Test
# ---------------------------------------------------------------------------

build: ## Build Docker images
	docker build -t sparqai-backend ./backend
	docker build --build-arg NEXT_PUBLIC_API_URL=https://api.sparqai.com/api/v1 -t sparqai-frontend ./frontend

test: ## Run all tests
	cd backend && pytest tests -v || true
	cd frontend && npm test -- --run || true

test-backend: ## Run backend tests only
	cd backend && pytest tests -v

test-frontend: ## Run frontend tests only
	cd frontend && npm test -- --run

# ---------------------------------------------------------------------------
# Linting
# ---------------------------------------------------------------------------

lint: ## Lint both backend (ruff) and frontend (eslint)
	@$(MAKE) lint-backend
	@$(MAKE) lint-frontend

lint-backend: ## Lint Python code with ruff
	cd backend && python -m ruff check . && python -m ruff format --check .

lint-frontend: ## Lint TypeScript code with eslint
	cd frontend && npm run lint

lint-fix: ## Auto-fix lint issues in both backend and frontend
	cd backend && python -m ruff check --fix . && python -m ruff format .
	cd frontend && npm run lint -- --fix || true

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

db-migrate: ## Run Alembic migrations
	cd backend && alembic upgrade head

db-revision: ## Create a new migration (usage: make db-revision MSG="add column")
	cd backend && alembic revision --autogenerate -m "$(MSG)"

db-downgrade: ## Rollback last migration
	cd backend && alembic downgrade -1

db-check: ## Check if models are in sync with migrations
	cd backend && alembic check

db-seed: ## Seed demo data (requires running backend)
	curl -X POST http://localhost:8000/api/v1/seed -H "Authorization: Bearer $$(cat .token 2>/dev/null || echo 'no-token')"

# ---------------------------------------------------------------------------
# Deployment
# ---------------------------------------------------------------------------

deploy: ## Deploy all to AWS
	bash scripts/deploy.sh all

deploy-backend: ## Deploy backend only
	bash scripts/deploy.sh backend

deploy-frontend: ## Deploy frontend only
	bash scripts/deploy.sh frontend

# ---------------------------------------------------------------------------
# Infrastructure
# ---------------------------------------------------------------------------

infra-init: ## Initialize Terraform
	cd infra/terraform && terraform init

infra-plan: ## Plan infrastructure changes
	cd infra/terraform && terraform plan

infra-apply: ## Apply infrastructure changes
	cd infra/terraform && terraform apply

infra-output: ## Show Terraform outputs
	cd infra/terraform && terraform output

# ---------------------------------------------------------------------------
# Monitoring & Health
# ---------------------------------------------------------------------------

health: ## Check health of local services
	@echo "--- Backend ---"
	@curl -sf http://localhost:8000/health && echo " OK" || echo " FAIL"
	@echo "--- Frontend ---"
	@curl -sf http://localhost:3000/ > /dev/null && echo " OK" || echo " FAIL"

health-prod: ## Check health of production services
	@echo "--- API ---"
	@curl -sf https://api.sparqai.com/health && echo " OK" || echo " FAIL"
	@echo "--- App ---"
	@curl -sf https://app.sparqai.com/ > /dev/null && echo " OK" || echo " FAIL"

logs-backend: ## Tail backend logs from CloudWatch
	aws logs tail /ecs/sparqai-production/backend --follow --region us-east-1

logs-frontend: ## Tail frontend logs from CloudWatch
	aws logs tail /ecs/sparqai-production/frontend --follow --region us-east-1

status: ## Show ECS service status
	@echo "--- Backend ---"
	@aws ecs describe-services --cluster sparqai-production-cluster --services sparqai-production-backend --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount,Deployments:deployments[*].{Status:rolloutState,Running:runningCount}}' --output table --region us-east-1 2>/dev/null || echo "Not deployed yet"
	@echo ""
	@echo "--- Frontend ---"
	@aws ecs describe-services --cluster sparqai-production-cluster --services sparqai-production-frontend --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount,Deployments:deployments[*].{Status:rolloutState,Running:runningCount}}' --output table --region us-east-1 2>/dev/null || echo "Not deployed yet"

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

clean: ## Remove Python and Node build artifacts
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find backend -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf frontend/.next frontend/node_modules/.cache
	rm -f backend/test.db backend/test_refactor.db

docker-clean: ## Remove dangling Docker images and stopped containers
	docker system prune -f
	docker image prune -f
