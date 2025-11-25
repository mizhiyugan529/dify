"""add consultation brief to messages

Revision ID: 6a9b6b4a2e0a
Revises: b5ec8d93926b
Create Date: 2026-01-05 12:30:00.000000

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "6a9b6b4a2e0a"
down_revision = "b5ec8d93926b"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("messages", sa.Column("consultation_brief", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("messages", "consultation_brief")
