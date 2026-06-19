#!/bin/bash
# ============================================================================
# SparqAI — Deploy to AWS ECS
# Usage: ./scripts/deploy.sh [backend|frontend|all]
# ============================================================================
set -euo pipefail

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_BACKEND="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/sparqai/backend"
ECR_FRONTEND="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/sparqai/frontend"
ECS_CLUSTER="sparqai-production-cluster"
BACKEND_SERVICE="sparqai-production-backend"
FRONTEND_SERVICE="sparqai-production-frontend"
HEALTH_CHECK_URL="https://api.${DOMAIN:-sparqai.com}/health"
HEALTH_CHECK_RETRIES=10
HEALTH_CHECK_INTERVAL=15

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[DEPLOY]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

COMPONENT="${1:-all}"
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Login to ECR
log "Authenticating with ECR..."
aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Save the current task definition ARN for rollback
get_current_task_def() {
  local service_name="$1"
  aws ecs describe-services \
    --cluster "$ECS_CLUSTER" \
    --services "$service_name" \
    --query 'services[0].taskDefinition' \
    --output text \
    --region "$AWS_REGION" 2>/dev/null || echo "none"
}

# Health check with retries
health_check() {
  local url="$1"
  local label="$2"
  log "Running health check for $label at $url..."
  for i in $(seq 1 "$HEALTH_CHECK_RETRIES"); do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    if [ "$STATUS" = "200" ]; then
      log "Health check passed for $label (attempt $i)"
      return 0
    fi
    warn "Attempt $i/$HEALTH_CHECK_RETRIES: HTTP $STATUS, retrying in ${HEALTH_CHECK_INTERVAL}s..."
    sleep "$HEALTH_CHECK_INTERVAL"
  done
  err "Health check failed for $label after $HEALTH_CHECK_RETRIES attempts"
}

# Rollback to previous task definition
rollback() {
  local service_name="$1"
  local prev_task_def="$2"
  if [ "$prev_task_def" = "none" ]; then
    warn "No previous task definition found for $service_name, cannot rollback"
    return 1
  fi
  warn "Rolling back $service_name to $prev_task_def..."
  aws ecs update-service \
    --cluster "$ECS_CLUSTER" \
    --service "$service_name" \
    --task-definition "$prev_task_def" \
    --force-new-deployment \
    --region "$AWS_REGION" > /dev/null
  aws ecs wait services-stable \
    --cluster "$ECS_CLUSTER" \
    --services "$service_name" \
    --region "$AWS_REGION" 2>/dev/null && \
    log "Rollback complete for $service_name" || \
    warn "Rollback may not have stabilized for $service_name"
}

deploy_backend() {
  local prev_task_def
  prev_task_def=$(get_current_task_def "$BACKEND_SERVICE")
  log "Previous backend task def: $prev_task_def"

  log "Building backend image..."
  docker build -t sparqai-backend:latest -t sparqai-backend:"$GIT_SHA" ./backend

  log "Tagging and pushing backend..."
  docker tag sparqai-backend:latest "$ECR_BACKEND:latest"
  docker tag sparqai-backend:"$GIT_SHA" "$ECR_BACKEND:$GIT_SHA"
  docker push "$ECR_BACKEND:latest"
  docker push "$ECR_BACKEND:$GIT_SHA"

  log "Updating backend ECS service..."
  aws ecs update-service \
    --cluster "$ECS_CLUSTER" \
    --service "$BACKEND_SERVICE" \
    --force-new-deployment \
    --region "$AWS_REGION" > /dev/null

  log "Backend deployment triggered (image: $GIT_SHA)"

  wait_for_stable "$BACKEND_SERVICE"

  # Health check with rollback on failure
  if ! health_check "$HEALTH_CHECK_URL" "backend"; then
    rollback "$BACKEND_SERVICE" "$prev_task_def"
    return 1
  fi
}

deploy_frontend() {
  local prev_task_def
  prev_task_def=$(get_current_task_def "$FRONTEND_SERVICE")
  log "Previous frontend task def: $prev_task_def"

  log "Building frontend image..."
  docker build \
    --build-arg NEXT_PUBLIC_API_URL="https://api.${DOMAIN:-sparqai.com}/api/v1" \
    -t sparqai-frontend:latest \
    -t sparqai-frontend:"$GIT_SHA" \
    ./frontend

  log "Tagging and pushing frontend..."
  docker tag sparqai-frontend:latest "$ECR_FRONTEND:latest"
  docker tag sparqai-frontend:"$GIT_SHA" "$ECR_FRONTEND:$GIT_SHA"
  docker push "$ECR_FRONTEND:latest"
  docker push "$ECR_FRONTEND:$GIT_SHA"

  log "Updating frontend ECS service..."
  aws ecs update-service \
    --cluster "$ECS_CLUSTER" \
    --service "$FRONTEND_SERVICE" \
    --force-new-deployment \
    --region "$AWS_REGION" > /dev/null

  log "Frontend deployment triggered (image: $GIT_SHA)"

  wait_for_stable "$FRONTEND_SERVICE"

  # Health check with rollback on failure
  if ! health_check "https://app.${DOMAIN:-sparqai.com}/" "frontend"; then
    rollback "$FRONTEND_SERVICE" "$prev_task_def"
    return 1
  fi
}

wait_for_stable() {
  local service_name="$1"
  log "Waiting for $service_name to stabilize..."
  aws ecs wait services-stable \
    --cluster "$ECS_CLUSTER" \
    --services "$service_name" \
    --region "$AWS_REGION" 2>/dev/null && \
    log "$service_name is stable!" || \
    warn "$service_name stabilization timed out — check AWS console"
}

DEPLOY_SUCCESS=true

case "$COMPONENT" in
  backend)
    deploy_backend || DEPLOY_SUCCESS=false
    ;;
  frontend)
    deploy_frontend || DEPLOY_SUCCESS=false
    ;;
  all)
    deploy_backend || DEPLOY_SUCCESS=false
    deploy_frontend || DEPLOY_SUCCESS=false
    ;;
  *)
    err "Usage: $0 [backend|frontend|all]"
    ;;
esac

if [ "$DEPLOY_SUCCESS" = true ]; then
  log "Deployment complete! (commit: $GIT_SHA)"
else
  err "Deployment completed with failures. Check logs above. (commit: $GIT_SHA)"
fi
