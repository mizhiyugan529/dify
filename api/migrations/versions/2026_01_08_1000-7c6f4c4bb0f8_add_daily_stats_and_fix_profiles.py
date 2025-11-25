"""add daily stats and ensure patient profile fields

Revision ID: 7c6f4c4bb0f8
Revises: 4f0d9db7e6c4
Create Date: 2026-01-08 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

import models as models


# revision identifiers, used by Alembic.
revision = "7c6f4c4bb0f8"
down_revision = "4f0d9db7e6c4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "daily_app_stats",
        sa.Column("id", models.types.StringUUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("tenant_id", models.types.StringUUID(), nullable=False),
        sa.Column("app_id", models.types.StringUUID(), nullable=False),
        sa.Column("stats_date", sa.Date(), nullable=False),
        sa.Column("conversation_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("new_profile_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("brief_summary", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="daily_app_stats_pkey"),
        sa.UniqueConstraint("tenant_id", "app_id", "stats_date", name="uq_daily_app_stats_date"),
    )
    with op.batch_alter_table("daily_app_stats", schema=None) as batch_op:
        batch_op.create_index("daily_app_stats_app_date_idx", ["app_id", "stats_date"], unique=False)

    # ensure patient_profiles columns exist and types are correct
    op.execute("ALTER TABLE patient_profiles DROP CONSTRAINT IF EXISTS patient_profiles_end_user_fk")
    op.execute("ALTER TABLE patient_profiles ALTER COLUMN end_user_id TYPE VARCHAR(255)")
    op.execute("ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS nickname VARCHAR(255)")
    op.execute("ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS emotion TEXT")
    op.execute("ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS compliance TEXT")
    op.execute("ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS communication_style TEXT")
    op.execute("ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS health_behavior TEXT")


def downgrade():
    op.execute("ALTER TABLE patient_profiles DROP COLUMN IF EXISTS health_behavior")
    op.execute("ALTER TABLE patient_profiles DROP COLUMN IF EXISTS communication_style")
    op.execute("ALTER TABLE patient_profiles DROP COLUMN IF EXISTS compliance")
    op.execute("ALTER TABLE patient_profiles DROP COLUMN IF EXISTS emotion")
    op.execute("ALTER TABLE patient_profiles DROP COLUMN IF EXISTS nickname")
    op.execute("ALTER TABLE patient_profiles ALTER COLUMN end_user_id TYPE UUID USING end_user_id::uuid")
    op.execute(
        "ALTER TABLE patient_profiles ADD CONSTRAINT patient_profiles_end_user_fk FOREIGN KEY (end_user_id) REFERENCES end_users(id) ON DELETE CASCADE"
    )
    op.drop_index("daily_app_stats_app_date_idx", table_name="daily_app_stats")
    op.drop_table("daily_app_stats")
