#!/bin/bash
# 실행: bash k8s/create-secrets.sh [dev|prod]

set -e

NAMESPACE=${1:-dev}

if [ ! -f .env ]; then
  echo ".env 파일이 없습니다. .env.example을 복사해주세요."
  echo "cp .env.example .env"
  exit 1
fi

source .env

# postgres-secret
kubectl create secret generic postgres-secret \
  --namespace="$NAMESPACE" \
  --from-literal=POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  --dry-run=client -o yaml | kubectl apply -f -

# app-secret (backend 컨테이너 envFrom으로 주입)
kubectl create secret generic app-secret \
  --namespace="$NAMESPACE" \
  --from-literal=DATABASE_URL="postgresql+asyncpg://todayme:${POSTGRES_PASSWORD}@postgres-svc:5432/todayme" \
  --from-literal=REDIS_URL="redis://redis-svc:6379" \
  --from-literal=GOOGLE_CLIENT_ID="$GOOGLE_CLIENT_ID" \
  --from-literal=GOOGLE_CLIENT_SECRET="$GOOGLE_CLIENT_SECRET" \
  --from-literal=GOOGLE_REDIRECT_URI="${GOOGLE_REDIRECT_URI:-http://localhost/api/auth/google/callback}" \
  --from-literal=JWT_SECRET="$JWT_SECRET" \
  --from-literal=FRONTEND_URL="${FRONTEND_URL:-http://localhost}" \
  --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY" \
  --from-literal=YOUTUBE_API_KEY="$YOUTUBE_API_KEY" \
  --from-literal=GOOGLE_MAPS_API_KEY="${GOOGLE_MAPS_API_KEY}" \
  --from-literal=LANGSMITH_API_KEY="$LANGSMITH_API_KEY" \
  --from-literal=LANGSMITH_TRACING="${LANGSMITH_TRACING:-false}" \
  --from-literal=LANGSMITH_PROJECT="${LANGSMITH_PROJECT:-today-me}" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "✓ postgres-secret, app-secret 생성 완료 (namespace: $NAMESPACE)"
