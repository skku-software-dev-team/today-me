import uuid
from datetime import datetime, timezone
from sqlalchemy import SmallInteger, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector

from app.core.database import Base


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 입력
    mood: Mapped[str] = mapped_column(Text, nullable=False)
    weather: Mapped[str | None] = mapped_column(Text)
    energy: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    location_district: Mapped[str | None] = mapped_column(Text)  # 동/구 단위만 저장

    # 에이전트 결과
    music_picks: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    place_picks: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    food_picks: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    style_picks: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    moodboard_url: Mapped[str | None] = mapped_column(Text)

    # 피드백: {"music-0": {"score": 1, "comment": "..."}, "place-1": {"score": -1}}
    feedback: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ReportEmbedding(Base):
    __tablename__ = "report_embeddings"

    report_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("daily_reports.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)  # 유저별 필터링용 역정규화

    embedding: Mapped[list] = mapped_column(Vector(1536))   # text-embedding-3-small
    embed_text: Mapped[str] = mapped_column(Text, nullable=False)  # 디버깅용 원문
    model: Mapped[str] = mapped_column(Text, nullable=False, default="text-embedding-3-small")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
