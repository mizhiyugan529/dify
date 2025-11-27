from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select

from extensions.ext_database import db
from models import Conversation, PatientProfile
from models.brief import ConversationBrief
from models.daily_stats import DailyAppStat
from models.model import App


class StatsService:
    CALM_VALUES = {"平静", "放松"}
    ANXIOUS_VALUES = {"焦虑", "担心"}
    TENSE_VALUES = {"紧张"}
    CONFUSED_VALUES = {"迷茫", "困惑"}
    FEAR_VALUES = {"恐惧"}
    EMPTY_VALUES = {"没有", ""}

    EMOTION_CATEGORIES = ("calm", "anxious", "tense", "confused", "fearful")
    ALERT_EMOTION_CATEGORIES = {"anxious", "fearful", "tense"}

    @classmethod
    def summary(cls, app_model: App) -> dict[str, Any]:
        today = date.today()
        start_current_month = date(today.year, today.month, 1)
        start_next_month = cls._shift_month(start_current_month, 1)
        start_previous_month = cls._shift_month(start_current_month, -1)
        tomorrow = today + timedelta(days=1)
        previous_period_end = min(start_previous_month + timedelta(days=today.day), start_current_month)

        total_conversations = cls._count_total_conversations(app_model)
        current_month_conversations = cls._count_conversations_between(app_model, start_current_month, tomorrow)
        last_month_conversations = cls._count_conversations_between(
            app_model, start_previous_month, previous_period_end
        )

        conversation_month_over_month_rate = cls._calculate_month_over_month_rate(
            current_month_conversations, last_month_conversations
        )

        new_profiles_current_month = cls._count_profiles_between(app_model, start_current_month, tomorrow)
        today_conversations = cls._count_conversations_between(app_model, today, tomorrow)
        new_profiles_today = cls._count_profiles_between(app_model, today, tomorrow)

        brief_summary = cls._build_brief_summary(app_model)
        emotion_distribution = cls._collect_emotion_distribution(app_model)
        emotion_alert_count, emotion_alert_user_ids = cls._collect_emotion_alerts(
            app_model, start_current_month, tomorrow
        )

        cls._upsert_daily(
            app_model,
            today,
            today_conversations,
            new_profiles_today,
            brief_summary,
            emotion_distribution,
        )

        return {
            "total_conversations": total_conversations,
            "current_month_conversations": current_month_conversations,
            "last_month_conversations": last_month_conversations,
            "conversation_month_over_month_rate": conversation_month_over_month_rate,
            "emotion_alert_count": emotion_alert_count,
            "emotion_alert_user_ids": emotion_alert_user_ids,
            "new_profiles_current_month": new_profiles_current_month,
            "brief_summary": brief_summary,
            "emotion_distribution": emotion_distribution,
        }

    @staticmethod
    def _shift_month(current_month: date, delta: int) -> date:
        month_index = current_month.month - 1 + delta
        year = current_month.year + month_index // 12
        month = month_index % 12 + 1
        return date(year, month, 1)

    @classmethod
    def _count_conversations_between(cls, app_model: App, start_date: date, end_date: date) -> int:
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.min.time())
        return (
            db.session.scalar(
                select(func.count()).where(
                    Conversation.app_id == app_model.id,
                    Conversation.is_deleted.is_(False),
                    Conversation.created_at >= start_dt,
                    Conversation.created_at < end_dt,
                )
            )
            or 0
        )

    @classmethod
    def _count_profiles_between(cls, app_model: App, start_date: date, end_date: date) -> int:
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.min.time())
        return (
            db.session.scalar(
                select(func.count()).where(
                    PatientProfile.app_id == app_model.id,
                    PatientProfile.created_at >= start_dt,
                    PatientProfile.created_at < end_dt,
                )
            )
            or 0
        )

    @classmethod
    def _count_total_conversations(cls, app_model: App) -> int:
        return (
            db.session.scalar(
                select(func.count()).where(Conversation.app_id == app_model.id, Conversation.is_deleted.is_(False))
            )
            or 0
        )

    @classmethod
    def _calculate_month_over_month_rate(cls, current_month_value: int, last_month_value: int) -> float:
        if last_month_value == 0:
            return 0.0
        return (current_month_value - last_month_value) / last_month_value

    @classmethod
    def _collect_emotion_distribution(cls, app_model: App) -> dict[str, int]:
        distribution: dict[str, int] = {category: 0 for category in cls.EMOTION_CATEGORIES}

        profiles = (
            db.session.query(PatientProfile.emotion.label("emotion"))
            .filter(PatientProfile.app_id == app_model.id)
            .all()
        )

        for (emotion,) in profiles:
            category = cls._normalize_emotion(emotion)
            distribution[category] += 1

        return distribution

    @classmethod
    def _collect_emotion_alerts(
        cls, app_model: App, start_date: date, end_date: date, limit: int = 3
    ) -> tuple[int, list[str]]:
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.min.time())

        alert_count = 0
        alert_user_ids: list[str] = []

        profiles = (
            db.session.query(
                PatientProfile.end_user_id.label("end_user_id"),
                PatientProfile.emotion.label("emotion"),
                PatientProfile.created_at.label("created_at"),
            )
            .filter(
                PatientProfile.app_id == app_model.id,
                PatientProfile.created_at >= start_dt,
                PatientProfile.created_at < end_dt,
            )
            .order_by(PatientProfile.created_at.desc())
            .all()
        )

        for end_user_id, emotion, _ in profiles:
            category = cls._normalize_emotion(emotion)
            if category in cls.ALERT_EMOTION_CATEGORIES:
                alert_count += 1
                if len(alert_user_ids) < limit:
                    alert_user_ids.append(end_user_id)

        return alert_count, alert_user_ids

    @classmethod
    def _normalize_emotion(cls, emotion: str | None) -> str:
        if emotion is None:
            return "calm"

        normalized = emotion.strip()
        if not normalized or normalized in cls.EMPTY_VALUES or normalized in cls.CALM_VALUES:
            return "calm"
        if normalized in cls.ANXIOUS_VALUES:
            return "anxious"
        if normalized in cls.TENSE_VALUES:
            return "tense"
        if normalized in cls.CONFUSED_VALUES:
            return "confused"
        if normalized in cls.FEAR_VALUES:
            return "fearful"
        return "calm"

    @classmethod
    def _build_brief_summary(cls, app_model: App) -> dict[str, int]:
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
        return {brief: count for brief, count in brief_rows}

    @classmethod
    def _upsert_daily(
        cls,
        app_model: App,
        stats_date: date,
        conversation_count: int,
        new_profile_count: int,
        brief_summary: dict[str, int],
        emotion_distribution: dict[str, int],
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
            record.emotion_distribution = emotion_distribution
        else:
            record = DailyAppStat(
                tenant_id=app_model.tenant_id,
                app_id=app_model.id,
                stats_date=stats_date,
                conversation_count=conversation_count,
                new_profile_count=new_profile_count,
                brief_summary=brief_summary,
                emotion_distribution=emotion_distribution,
            )
            db.session.add(record)
        db.session.commit()
