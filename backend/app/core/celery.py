from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "today-me",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.optimize"],  # 워커가 시작할 때 태스크를 등록한다
)

celery_app.conf.update(
    task_default_queue="default",  # k8s 워커의 --queues=default와 일치해야 한다
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Seoul",
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=60 * 60 * 24,
    task_soft_time_limit=120,  # 120초 후 SoftTimeLimitExceeded → retry 기회
    task_time_limit=180,  # 180초 후 강제 kill → worker 살아있음
    worker_max_tasks_per_child=50,  # 50개 처리 후 worker 재시작 → 메모리 누수 방지
)
