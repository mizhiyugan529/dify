"""add emotion distribution to daily_app_stats

Revision ID: 1f8b9ad3c7f2
Revises: 7c6f4c4bb0f8
Create Date: 2026-01-09 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "1f8b9ad3c7f2"
down_revision = "7c6f4c4bb0f8"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("daily_app_stats", schema=None) as batch_op:
        batch_op.add_column(sa.Column("emotion_distribution", sa.JSON(), nullable=False, server_default="{}"))


def downgrade():
    with op.batch_alter_table("daily_app_stats", schema=None) as batch_op:
        batch_op.drop_column("emotion_distribution")
