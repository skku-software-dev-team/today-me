#!/bin/bash
# 사용: bash redeploy.sh [backend|frontend|all]

set -e

TARGET=${1:-all}
NAMESPACE=${2:-dev}

redeploy_backend() {
  echo "==> backend 이미지 재빌드"
  docker build -t today-me-backend:latest ./backend
  echo "==> backend 롤링 재시작"
  kubectl rollout restart deployment/backend -n "$NAMESPACE"
  kubectl rollout status deployment/backend -n "$NAMESPACE"
}

redeploy_frontend() {
  echo "==> frontend 이미지 재빌드"
  docker build -t today-me-frontend:latest ./frontend
  echo "==> frontend 롤링 재시작"
  kubectl rollout restart deployment/frontend -n "$NAMESPACE"
  kubectl rollout status deployment/frontend -n "$NAMESPACE"
}

case "$TARGET" in
  backend)  redeploy_backend ;;
  frontend) redeploy_frontend ;;
  all)      redeploy_backend; redeploy_frontend ;;
esac

echo "==> 완료"
