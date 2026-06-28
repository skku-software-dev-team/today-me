param([string]$Namespace = "dev")

Write-Host "==> 이미지 빌드"
docker build -t today-me-backend:latest ./backend
docker build -t today-me-frontend:latest ./frontend

Write-Host "==> namespace 생성"
kubectl apply -f k8s/namespace.yaml

Write-Host "==> secrets 생성"
& "$PSScriptRoot\k8s\create-secrets.ps1" -Namespace $Namespace

Write-Host "==> postgres / redis 배포"
kubectl apply -f k8s/postgres/configmap.yaml
kubectl apply -f k8s/postgres/pvc.yaml
kubectl apply -f k8s/postgres/deployment.yaml
kubectl apply -f k8s/redis/deployment.yaml

Write-Host "==> backend / frontend 배포"
kubectl apply -f k8s/backend/deployment.yaml
kubectl apply -f k8s/frontend/deployment.yaml

Write-Host "==> ingress 적용"
kubectl apply -f k8s/ingress.yaml

Write-Host ""
Write-Host "==> Pod 상태 확인"
kubectl get pods -n $Namespace

Write-Host ""
Write-Host "==> 접속 주소: http://localhost"
