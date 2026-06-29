from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "today-me",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Seoul",
    task_acks_late=True,          # 태스크 완료 후 ack → 실패 시 재시도
    worker_prefetch_multiplier=1, # worker당 태스크 1개씩만
    result_expires=60 * 60 * 24, # 결과 24시간 보관
)
