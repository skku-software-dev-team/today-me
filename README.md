# today-me

## 시작하기

### 사전 준비
1. [Docker Desktop](https://www.docker.com/products/docker-desktop/) 설치
2. Docker Desktop → Settings → Kubernetes → **Enable Kubernetes** 체크 → Apply & Restart
3. `.env` 파일 생성
```bash
cp .env.example .env
# .env 열어서 값 채우기
```

### 배포

**Windows (PowerShell)**
```powershell
.\deploy-local.ps1
```

**Mac / Linux**
```bash
bash deploy-local.sh
```

접속: http://localhost

---

## 디렉토리 구조

```
today-me/
├── backend/                        # FastAPI
│   ├── app/
│   │   ├── main.py
│   │   ├── core/                   # 설정, JWT, DB, Redis
│   │   ├── models/                 # SQLAlchemy 모델
│   │   ├── routers/                # API 라우터
│   │   └── services/               # 비즈니스 로직
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                       # React + Vite + Tailwind
│   ├── src/
│   │   ├── hooks/                  # useAuth
│   │   ├── lib/                    # api fetch 유틸
│   │   └── pages/                  # Login, Callback, Home
│   ├── Dockerfile
│   └── nginx.conf
├── k8s/
│   ├── namespace.yaml
│   ├── ingress.yaml
│   ├── create-secrets.sh           # Secret 생성 (Mac/Linux)
│   ├── create-secrets.ps1          # Secret 생성 (Windows)
│   ├── postgres/                   # ConfigMap, PVC, Deployment
│   ├── redis/
│   ├── backend/
│   └── frontend/
├── deploy-local.sh                 # 전체 배포 (Mac/Linux)
├── deploy-local.ps1                # 전체 배포 (Windows)
├── .env.example
└── .gitignore
```
