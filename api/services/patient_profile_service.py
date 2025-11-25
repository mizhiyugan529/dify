from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from extensions.ext_database import db
from libs.datetime_utils import naive_utc_now
from models.brief import ConversationBrief
from models.model import App, PatientProfile


class PatientProfileService:
    """Manage patient specific profile data for an end user."""

    @classmethod
    def get_or_none(cls, app_model: App, user_id: str) -> PatientProfile | None:
        return (
            db.session.query(PatientProfile)
            .where(
                PatientProfile.tenant_id == app_model.tenant_id,
                PatientProfile.app_id == app_model.id,
                PatientProfile.end_user_id == user_id,
            )
            .first()
        )

    @classmethod
    def upsert(cls, app_model: App, user_id: str, payload: Mapping[str, Any]) -> PatientProfile:
        profile = cls.get_or_none(app_model, user_id)
        if not profile:
            profile = PatientProfile(
                tenant_id=app_model.tenant_id,
                app_id=app_model.id,
                end_user_id=user_id,
            )
            db.session.add(profile)

        profile.nickname = payload.get("nickname")
        profile.emotion = payload.get("emotion")
        profile.compliance = payload.get("compliance")
        profile.communication_style = payload.get("communication_style")
        profile.health_behavior = payload.get("health_behavior")
        profile.updated_at = naive_utc_now()

        db.session.commit()
        return profile

    @classmethod
    def search(
        cls,
        *,
        app_model: App,
        user_id: str | None,
        user_ids: str | None,
        nickname: str | None,
        emotion: str | None,
        compliance: str | None,
        communication_style: str | None,
        health_behavior: str | None,
        page: int,
        limit: int,
        sort_by: str,
    ) -> dict[str, Any]:
        stmt = db.select(PatientProfile).where(
            PatientProfile.tenant_id == app_model.tenant_id,
            PatientProfile.app_id == app_model.id,
        )

        if user_ids:
            id_list = [i.strip() for i in user_ids.split(",") if i.strip()]
            if id_list:
                stmt = stmt.where(PatientProfile.end_user_id.in_(id_list))
        elif user_id:
            stmt = stmt.where(PatientProfile.end_user_id == user_id)

        if nickname:
            stmt = stmt.where(PatientProfile.nickname.ilike(f"%{nickname}%"))
        if emotion:
            stmt = stmt.where(PatientProfile.emotion == emotion)
        if compliance:
            stmt = stmt.where(PatientProfile.compliance == compliance)
        if communication_style:
            stmt = stmt.where(PatientProfile.communication_style == communication_style)
        if health_behavior:
            stmt = stmt.where(PatientProfile.health_behavior == health_behavior)

        sort_field = "updated_at"
        sort_dir = db.desc
        if sort_by in {"created_at", "-created_at"}:
            sort_field = "created_at"
        if not sort_by.startswith("-"):
            sort_dir = db.asc

        page = max(page, 1)
        limit = max(limit, 1)
        offset = (page - 1) * limit

        total = db.session.scalar(db.select(db.func.count()).select_from(stmt.subquery())) or 0
        rows = db.session.scalars(stmt.order_by(sort_dir(getattr(PatientProfile, sort_field))).offset(offset).limit(limit)).all()
        has_more = offset + len(rows) < total

        user_ids_set = {row.end_user_id for row in rows}
        latest_brief_map: dict[str, dict[str, Any]] = {}
        if user_ids_set:
            latest_rows = (
                db.session.query(
                    ConversationBrief.user_id,
                    ConversationBrief.conversation_id,
                    ConversationBrief.brief,
                    ConversationBrief.updated_at,
                )
                .filter(ConversationBrief.app_id == app_model.id, ConversationBrief.user_id.in_(user_ids_set))
                .order_by(ConversationBrief.user_id, ConversationBrief.updated_at.desc())
                .distinct(ConversationBrief.user_id)
                .all()
            )
            for uid, cid, brief, updated_at in latest_rows:
                latest_brief_map[uid] = {
                    "conversation_id": cid,
                    "brief": brief,
                    "updated_at": updated_at,
                }

        data = []
        for row in rows:
            data.append(
                {
                    "id": row.id,
                    "tenant_id": row.tenant_id,
                    "app_id": row.app_id,
                    "end_user_id": row.end_user_id,
                    "nickname": row.nickname,
                    "emotion": row.emotion,
                    "compliance": row.compliance,
                    "communication_style": row.communication_style,
                    "health_behavior": row.health_behavior,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                    "latest_brief": (latest_brief_map.get(row.end_user_id) or {}).get("brief"),
                    "latest_brief_conversation_id": (latest_brief_map.get(row.end_user_id) or {}).get(
                        "conversation_id"
                    ),
                }
            )

        return {
            "profile": None,
            "data": data,
            "page": page,
            "limit": limit,
            "total": total,
            "has_more": has_more,
        }
