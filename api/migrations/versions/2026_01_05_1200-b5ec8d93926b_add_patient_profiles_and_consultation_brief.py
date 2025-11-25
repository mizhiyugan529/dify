"""add patient profiles table and consultation brief column

Revision ID: b5ec8d93926b
Revises: 669ffd70119c
Create Date: 2026-01-05 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

import models as models

# revision identifiers, used by Alembic.
revision = "b5ec8d93926b"
down_revision = "669ffd70119c"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("conversations", sa.Column("consultation_brief", sa.Text(), nullable=True))

    op.create_table(
        "patient_profiles",
        sa.Column("id", models.types.StringUUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("tenant_id", models.types.StringUUID(), nullable=False),
        sa.Column("app_id", models.types.StringUUID(), nullable=False),
        sa.Column("end_user_id", models.types.StringUUID(), nullable=False),
        sa.Column("personality", sa.Text(), nullable=True),
        sa.Column("current_mood", sa.Text(), nullable=True),
        sa.Column("concerns", sa.Text(), nullable=True),
        sa.Column("chronic_conditions_self_reported", sa.Text(), nullable=True),
        sa.Column("chronic_conditions_confirmed", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["end_user_id"], ["end_users.id"], name="patient_profiles_end_user_fk", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="patient_profile_pkey"),
        sa.UniqueConstraint("tenant_id", "app_id", "end_user_id", name="uq_patient_profile_end_user"),
    )
    with op.batch_alter_table("patient_profiles", schema=None) as batch_op:
        batch_op.create_index("patient_profile_app_end_user_idx", ["app_id", "end_user_id"], unique=False)


def downgrade():
    op.drop_index("patient_profile_app_end_user_idx", table_name="patient_profiles")
    op.drop_table("patient_profiles")
    op.drop_column("conversations", "consultation_brief")
