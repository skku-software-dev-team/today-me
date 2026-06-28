param(
    [ValidateSet("backend", "frontend", "all")]
    [string]$Target = "all",
    [string]$Namespace = "dev"
)

function Redeploy-Backend {
    Write-Host "==> backend 이미지 재빌드"
    docker build -t today-me-backend:latest ./backend
    Write-Host "==> backend 롤링 재시작"
    kubectl rollout restart deployment/backend -n $Namespace
    kubectl rollout status deployment/backend -n $Namespace
}

function Redeploy-Frontend {
    Write-Host "==> frontend 이미지 재빌드"
    docker build -t today-me-frontend:latest ./frontend
    Write-Host "==> frontend 롤링 재시작"
    kubectl rollout restart deployment/frontend -n $Namespace
    kubectl rollout status deployment/frontend -n $Namespace
}

switch ($Target) {
    "backend"  { Redeploy-Backend }
    "frontend" { Redeploy-Frontend }
    "all"      { Redeploy-Backend; Redeploy-Frontend }
}

Write-Host "==> 완료"
