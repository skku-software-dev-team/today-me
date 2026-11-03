"""make optimized_prompts per user

Revision ID: 003
Revises: 002
Create Date: 2026-11-03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 기존 행은 소유자가 없는 공용 프롬프트라 옮길 수 없다. 다음 개선 때 다시 만들어진다.
    op.execute("DELETE FROM optimized_prompts")
    op.drop_constraint("optimized_prompts_pkey", "optimized_prompts", type_="primary")
    op.add_column(
        "optimized_prompts",
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    op.create_primary_key("optimized_prompts_pkey", "optimized_prompts", ["user_id", "agent_type"])


def downgrade() -> None:
    op.execute("DELETE FROM optimized_prompts")
    op.drop_constraint("optimized_prompts_pkey", "optimized_prompts", type_="primary")
    op.drop_column("optimized_prompts", "user_id")
    op.create_primary_key("optimized_prompts_pkey", "optimized_prompts", ["agent_type"])
