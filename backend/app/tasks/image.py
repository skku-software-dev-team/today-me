import logging
import os

from celery.exceptions import SoftTimeLimitExceeded
from openai import OpenAI

from app.agents.moodboard.agent import build_gpt_image_prompt
from app.core.celery import celery_app

logger = logging.getLogger(__name__)


def _generate_image(mood: str, weather: str, energy: int) -> str:
    prompt = build_gpt_image_prompt(mood=mood, weather=weather, energy=energy)
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), timeout=100)
    response = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1536x1024",
        n=1,
    )
    item = response.data[0]
    if getattr(item, "url", None):
        return item.url
    return f"data:image/png;base64,{item.b64_json}"


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    name="tasks.generate_moodboard",
    ignore_result=True,  # DB에 직접 쓰므로 Redis에 결과 저장 불필요
)
def generate_moodboard(self, report_id: str, mood: str, weather: str, energy: int):
    from sqlalchemy import create_engine, text

    from app.core.config import settings

    logger.info(f"[moodboard] 시작 report_id={report_id}")

    try:
        image_url = _generate_image(mood, weather, energy)

        sync_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        engine = create_engine(sync_url)
        with engine.connect() as conn:
            conn.execute(
                text("UPDATE daily_states SET moodboard = :url WHERE id = :id"),
                {"url": image_url, "id": report_id},
            )
            conn.commit()

        logger.info(f"[moodboard] 완료 report_id={report_id} url={image_url}")

    except SoftTimeLimitExceeded:
        logger.error(f"[moodboard] 타임아웃 report_id={report_id}, 재시도 예정")
        raise self.retry(countdown=30) from None

    except Exception as exc:
        logger.error(f"[moodboard] 실패 report_id={report_id} error={exc}")
        raise self.retry(exc=exc) from exc
