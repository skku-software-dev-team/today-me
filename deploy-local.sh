#!/bin/bash
# Docker Desktop k8s 로컬 배포
# 실행: bash deploy-local.sh

set -e

NAMESPACE=${1:-dev}

echo "==> 이미지 빌드"
docker build -t today-me-backend:latest ./backend
docker build -t today-me-frontend:latest ./frontend

echo "==> namespace 생성"
kubectl apply -f k8s/namespace.yaml

echo "==> secrets 생성"
bash k8s/create-secrets.sh "$NAMESPACE"

echo "==> postgres / redis 배포"
kubectl apply -f k8s/postgres/configmap.yaml
kubectl apply -f k8s/postgres/pvc.yaml
kubectl apply -f k8s/postgres/deployment.yaml
kubectl apply -f k8s/redis/deployment.yaml

echo "==> backend / frontend 배포"
kubectl apply -f k8s/backend/deployment.yaml
kubectl apply -f k8s/frontend/deployment.yaml

echo ""
echo "==> Pod 상태 확인"
kubectl get pods -n "$NAMESPACE"

echo ""
# frontend NodePort 찾아서 출력
NODE_PORT=$(kubectl get svc frontend-svc -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "pending")
echo "==> 접속 주소: http://localhost:${NODE_PORT}"
