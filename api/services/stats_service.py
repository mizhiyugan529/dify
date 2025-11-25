from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select

from extensions.ext_database import db
from models import Conversation, PatientProfile
from models.brief import ConversationBrief
from models.daily_stats import DailyAppStat
from models.model import App


class StatsService:
    @classmethod
    def summary(cls, app_model: App) -> dict[str, Any]:
        today = date.today()
        yesterday = today - timedelta(days=1)
        day_before_yesterday = today - timedelta(days=2)

        total_conversations = db.session.scalar(
            select(func.count()).where(Conversation.app_id == app_model.id, Conversation.is_deleted == False)
        ) or 0

        today_count = db.session.scalar(
            select(func.count()).where(
                Conversation.app_id == app_model.id,
                Conversation.is_deleted == False,
                func.date(Conversation.created_at) == today,
            )
        ) or 0

        yesterday_count = db.session.scalar(
            select(func.count()).where(
                Conversation.app_id == app_model.id,
                Conversation.is_deleted == False,
                func.date(Conversation.created_at) == yesterday,
            )
        ) or 0

        day_before_count = db.session.scalar(
            select(func.count()).where(
                Conversation.app_id == app_model.id,
                Conversation.is_deleted == False,
                func.date(Conversation.created_at) == day_before_yesterday,
            )
        ) or 0

        # emotion filter
        emotion_list = ["焦虑", "紧张", "担心", "恐惧"]
        emotion_query = db.session.query(PatientProfile.end_user_id).filter(
            PatientProfile.app_id == app_model.id,
            PatientProfile.emotion.in_(emotion_list),
        )
        emotion_user_ids = [row.end_user_id for row in emotion_query.all()]

        new_profiles_today = db.session.scalar(
            select(func.count()).where(
                PatientProfile.app_id == app_model.id,
                func.date(PatientProfile.created_at) == today,
            )
        ) or 0

        # brief summary: count by brief text, exclude 空和“其他”
        brief_rows = (
            db.session.query(ConversationBrief.brief, func.count())
            .filter(
                ConversationBrief.app_id == app_model.id,
                ConversationBrief.brief.is_not(None),
                ConversationBrief.brief != "",
                ConversationBrief.brief != "其他",
            )
            .group_by(ConversationBrief.brief)
            .all()
        )
        brief_summary: dict[str, int] = {b: c for b, c in brief_rows}

        cls._upsert_daily(app_model, today, today_count, new_profiles_today, brief_summary)

        return {
            "total_conversations": total_conversations,
            "today_conversations": today_count,
            "conversation_delta_vs_previous": yesterday_count - day_before_count,
            "emotion_alert_count": len(emotion_user_ids),
            "emotion_alert_user_ids": emotion_user_ids,
            "new_profiles_today": new_profiles_today,
            "brief_summary": brief_summary,
        }

    @classmethod
    def _upsert_daily(
        cls, app_model: App, stats_date: date, conversation_count: int, new_profile_count: int, brief_summary: dict
    ) -> None:
        record = (
            db.session.query(DailyAppStat)
            .where(
                DailyAppStat.tenant_id == app_model.tenant_id,
                DailyAppStat.app_id == app_model.id,
                DailyAppStat.stats_date == stats_date,
            )
            .first()
        )
        if record:
            record.conversation_count = conversation_count
            record.new_profile_count = new_profile_count
            record.brief_summary = brief_summary
        else:
            record = DailyAppStat(
                tenant_id=app_model.tenant_id,
                app_id=app_model.id,
                stats_date=stats_date,
                conversation_count=conversation_count,
                new_profile_count=new_profile_count,
                brief_summary=brief_summary,
            )
            db.session.add(record)
        db.session.commit()
