FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip uninstall -y ecdsa
# ecdsa: python-jose[cryptography] 백엔드는 ecdsa를 런타임에 사용하지 않음.
# CVE-2024-23342(Minerva)는 upstream 패치 없음 → 미사용 패키지를 이미지에서 제거

COPY app/ ./app/

RUN useradd --no-create-home --uid 10001 appuser
USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
