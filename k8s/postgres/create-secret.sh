#!/bin/bash
# 팀원 모두 이 스크립트로 secret 생성
# .env 파일에서 값 읽어서 k8s secret으로 등록
# 실행: bash k8s/postgres/create-secret.sh

set -e

NAMESPACE=${1:-dev}

if [ ! -f .env ]; then
  echo ".env 파일이 없습니다. .env.example을 복사해서 만들어주세요."
  echo "cp .env.example .env"
  exit 1
fi

source .env

kubectl create secret generic postgres-secret \
  --namespace="$NAMESPACE" \
  --from-literal=POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  --from-literal=DATABASE_URL="postgresql://todayi:${POSTGRES_PASSWORD}@postgres-svc:5432/todayi" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "postgres-secret 생성 완료 (namespace: $NAMESPACE)"
