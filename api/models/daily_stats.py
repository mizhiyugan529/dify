import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base
from models.types import StringUUID


class DailyAppStat(Base):
    __tablename__ = "daily_app_stats"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="daily_app_stats_pkey"),
        sa.UniqueConstraint("tenant_id", "app_id", "stats_date", name="uq_daily_app_stats_date"),
        sa.Index("daily_app_stats_app_date_idx", "app_id", "stats_date"),
    )

    id: Mapped[str] = mapped_column(StringUUID, server_default=sa.text("uuid_generate_v4()"))
    tenant_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    app_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    stats_date = mapped_column(sa.Date, nullable=False)
    conversation_count = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    new_profile_count = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    brief_summary = mapped_column(sa.JSON, nullable=False, server_default="{}")
    emotion_distribution = mapped_column(sa.JSON, nullable=False, server_default="{}")
    created_at = mapped_column(sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"))
    updated_at = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), onupdate=sa.text("CURRENT_TIMESTAMP")
    )
