"""add optimized_prompts table

Revision ID: 002
Revises: 001
Create Date: 2026-07-02
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "optimized_prompts",
        sa.Column("agent_type", sa.Text(), primary_key=True),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("few_shot_demos", JSONB(), nullable=False, server_default="[]"),
        sa.Column("avg_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("optimized_prompts")
