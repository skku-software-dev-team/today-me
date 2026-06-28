param([string]$Namespace = "dev")

Write-Host "==> 전체 리소스 삭제"
kubectl delete -f k8s/frontend/deployment.yaml --ignore-not-found
kubectl delete -f k8s/backend/deployment.yaml --ignore-not-found
kubectl delete -f k8s/redis/deployment.yaml --ignore-not-found
kubectl delete -f k8s/postgres/deployment.yaml --ignore-not-found
kubectl delete -f k8s/postgres/pvc.yaml --ignore-not-found
kubectl delete -f k8s/postgres/configmap.yaml --ignore-not-found

Write-Host "==> secrets 삭제"
kubectl delete secret postgres-secret app-secret -n $Namespace --ignore-not-found

Write-Host "==> 완료. 재배포: .\deploy-local.ps1"
