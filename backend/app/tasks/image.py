import asyncio
import logging
from app.core.celery import celery_app

logger = logging.getLogger(__name__)


def _generate_image(mood: str, weather: str, energy: int) -> str:
    """
    실제 이미지 생성 API 호출 위치.
    현재는 mock — DALL·E / Stable Diffusion으로 교체 예정.
    """
    # TODO: 실제 API 연동
    return f"https://picsum.photos/seed/{mood[:8]}/800/600"


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    name="tasks.generate_moodboard",
)
def generate_moodboard(self, report_id: str, mood: str, weather: str, energy: int):
    from sqlalchemy import create_engine, text
    from app.core.config import settings

    logger.info(f"[moodboard] 시작 report_id={report_id}")

    try:
        image_url = _generate_image(mood, weather, energy)

        # asyncpg는 sync context에서 못 쓰니까 psycopg2 URL로 변환
        sync_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        engine = create_engine(sync_url)
        with engine.connect() as conn:
            conn.execute(
                text("UPDATE daily_states SET moodboard = :url WHERE id = :id"),
                {"url": image_url, "id": report_id},
            )
            conn.commit()

        logger.info(f"[moodboard] 완료 report_id={report_id} url={image_url}")
        return {"report_id": report_id, "moodboard_url": image_url}

    except Exception as exc:
        logger.error(f"[moodboard] 실패 report_id={report_id} error={exc}")
        raise self.retry(exc=exc)
