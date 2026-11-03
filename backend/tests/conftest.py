"""app.core.config.Settings의 필수값을 테스트용 더미로 채운다. 실제 서비스에 연결하지 않는다."""

import os

os.environ.setdefault("GOOGLE_CLIENT_ID", "test")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test")
os.environ.setdefault("JWT_SECRET", "test-secret-for-unit-tests-only-32-bytes")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
