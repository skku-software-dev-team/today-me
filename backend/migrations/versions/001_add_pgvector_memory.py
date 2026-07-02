"""add pgvector memory tables

Revision ID: 001
Revises:
Create Date: 2026-06-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "daily_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mood", sa.Text, nullable=False),
        sa.Column("weather", sa.Text),
        sa.Column("energy", sa.SmallInteger, nullable=False),
        sa.Column("location_district", sa.Text),
        sa.Column("music_picks", JSONB, nullable=False, server_default="[]"),
        sa.Column("place_picks", JSONB, nullable=False, server_default="[]"),
        sa.Column("food_picks", JSONB, nullable=False, server_default="[]"),
        sa.Column("style_picks", JSONB, nullable=False, server_default="[]"),
        sa.Column("moodboard_url", sa.Text),
        sa.Column("feedback", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_daily_reports_user_id", "daily_reports", ["user_id"])

    op.create_table(
        "report_embeddings",
        sa.Column("report_id", UUID(as_uuid=True), sa.ForeignKey("daily_reports.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("embedding", sa.Text, nullable=False),  # 마이그레이션 시 TEXT로 생성 후 ALTER
        sa.Column("embed_text", sa.Text, nullable=False),
        sa.Column("model", sa.Text, nullable=False, server_default="text-embedding-3-small"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # TEXT → vector(1536) 로 변환 (pgvector 익스텐션 활성화 후에만 가능)
    op.execute("ALTER TABLE report_embeddings ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector")

    op.create_index("ix_report_embeddings_user_id", "report_embeddings", ["user_id"])

    # HNSW 인덱스 — 코사인 유사도 기반 top-k 조회
    # m=16: 노드당 최대 연결 수 (정확도↑ → 메모리↑)
    # ef_construction=64: 인덱스 빌드 탐색 너비 (정확도↑ → 빌드 시간↑)
    op.execute("""
        CREATE INDEX ix_report_embeddings_embedding_hnsw
        ON report_embeddings
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    op.drop_table("report_embeddings")
    op.drop_table("daily_reports")
