"""update patient profile fields and add conversation briefs

Revision ID: 4f0d9db7e6c4
Revises: 6a9b6b4a2e0a
Create Date: 2026-01-06 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

import models as models

# revision identifiers, used by Alembic.
revision = "4f0d9db7e6c4"
down_revision = "6a9b6b4a2e0a"
branch_labels = None
depends_on = None


def upgrade():
    # patient_profiles adjustments
    with op.batch_alter_table("patient_profiles", schema=None) as batch_op:
        batch_op.drop_constraint("patient_profiles_end_user_fk", type_="foreignkey")
        batch_op.alter_column(
            "end_user_id",
            existing_type=models.types.StringUUID(),
            type_=sa.String(length=255),
            existing_nullable=False,
        )
        batch_op.drop_column("personality")
        batch_op.drop_column("current_mood")
        batch_op.drop_column("concerns")
        batch_op.drop_column("chronic_conditions_self_reported")
        batch_op.drop_column("chronic_conditions_confirmed")
        batch_op.add_column(sa.Column("nickname", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("emotion", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("compliance", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("communication_style", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("health_behavior", sa.Text(), nullable=True))

    # conversation_briefs table
    op.create_table(
        "conversation_briefs",
        sa.Column("id", models.types.StringUUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("tenant_id", models.types.StringUUID(), nullable=False),
        sa.Column("app_id", models.types.StringUUID(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("conversation_id", models.types.StringUUID(), nullable=False),
        sa.Column("brief", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="conversation_brief_pkey"),
        sa.UniqueConstraint("tenant_id", "app_id", "user_id", "conversation_id", name="uq_brief_user_conversation"),
    )
    with op.batch_alter_table("conversation_briefs", schema=None) as batch_op:
        batch_op.create_index("conversation_brief_user_idx", ["app_id", "user_id", "updated_at"], unique=False)


def downgrade():
    op.drop_index("conversation_brief_user_idx", table_name="conversation_briefs")
    op.drop_table("conversation_briefs")

    with op.batch_alter_table("patient_profiles", schema=None) as batch_op:
        batch_op.drop_column("health_behavior")
        batch_op.drop_column("communication_style")
        batch_op.drop_column("compliance")
        batch_op.drop_column("emotion")
        batch_op.drop_column("nickname")
        batch_op.alter_column(
            "end_user_id",
            existing_type=sa.String(length=255),
            type_=models.types.StringUUID(),
            existing_nullable=False,
        )
        batch_op.create_foreign_key(
            "patient_profiles_end_user_fk",
            "end_users",
            ["end_user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.add_column(sa.Column("personality", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("current_mood", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("concerns", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("chronic_conditions_self_reported", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("chronic_conditions_confirmed", sa.Text(), nullable=True))
