import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base
from models.types import StringUUID


class ConversationBrief(Base):
    __tablename__ = "conversation_briefs"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="conversation_brief_pkey"),
        sa.UniqueConstraint("tenant_id", "app_id", "user_id", "conversation_id", name="uq_brief_user_conversation"),
        sa.Index("conversation_brief_user_idx", "app_id", "user_id", "updated_at"),
    )

    id: Mapped[str] = mapped_column(StringUUID, server_default=sa.text("uuid_generate_v4()"))
    tenant_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    app_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    user_id: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    conversation_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    brief = mapped_column(sa.Text)
    created_at = mapped_column(sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"))
    updated_at = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), onupdate=sa.text("CURRENT_TIMESTAMP")
    )
