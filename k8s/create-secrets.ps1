param([string]$Namespace = "dev")

if (-not (Test-Path ".env")) {
    Write-Error ".env 파일이 없습니다. .env.example을 복사해주세요. (cp .env.example .env)"
    exit 1
}

# .env 파싱
Get-Content ".env" | ForEach-Object {
    if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
        [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim())
    }
}

$POSTGRES_PASSWORD = [System.Environment]::GetEnvironmentVariable("POSTGRES_PASSWORD")
$GOOGLE_CLIENT_ID = [System.Environment]::GetEnvironmentVariable("GOOGLE_CLIENT_ID")
$GOOGLE_CLIENT_SECRET = [System.Environment]::GetEnvironmentVariable("GOOGLE_CLIENT_SECRET")
$GOOGLE_REDIRECT_URI = [System.Environment]::GetEnvironmentVariable("GOOGLE_REDIRECT_URI")
if (-not $GOOGLE_REDIRECT_URI) { $GOOGLE_REDIRECT_URI = "http://localhost/api/auth/google/callback" }
$JWT_SECRET = [System.Environment]::GetEnvironmentVariable("JWT_SECRET")
$FRONTEND_URL = [System.Environment]::GetEnvironmentVariable("FRONTEND_URL")
if (-not $FRONTEND_URL) { $FRONTEND_URL = "http://localhost" }

# postgres-secret
kubectl create secret generic postgres-secret `
    --namespace="$Namespace" `
    --from-literal=POSTGRES_PASSWORD="$POSTGRES_PASSWORD" `
    --dry-run=client -o yaml | kubectl apply -f -

# app-secret
kubectl create secret generic app-secret `
    --namespace="$Namespace" `
    --from-literal=DATABASE_URL="postgresql+asyncpg://todayme:${POSTGRES_PASSWORD}@postgres-svc:5432/todayme" `
    --from-literal=REDIS_URL="redis://redis-svc:6379" `
    --from-literal=GOOGLE_CLIENT_ID="$GOOGLE_CLIENT_ID" `
    --from-literal=GOOGLE_CLIENT_SECRET="$GOOGLE_CLIENT_SECRET" `
    --from-literal=GOOGLE_REDIRECT_URI="$GOOGLE_REDIRECT_URI" `
    --from-literal=JWT_SECRET="$JWT_SECRET" `
    --from-literal=FRONTEND_URL="$FRONTEND_URL" `
    --dry-run=client -o yaml | kubectl apply -f -

Write-Host "✓ postgres-secret, app-secret 생성 완료 (namespace: $Namespace)"
