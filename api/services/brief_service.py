from __future__ import annotations

from typing import Any

from sqlalchemy import asc, desc, func, select

from extensions.ext_database import db
from models import PatientProfile
from models.brief import ConversationBrief
from models.model import App


class BriefService:
    @classmethod
    def upsert(cls, app_model: App, user_id: str, conversation_id: str, brief: str) -> ConversationBrief:
        existing: ConversationBrief | None = (
            db.session.query(ConversationBrief)
            .where(
                ConversationBrief.tenant_id == app_model.tenant_id,
                ConversationBrief.app_id == app_model.id,
                ConversationBrief.user_id == user_id,
                ConversationBrief.conversation_id == conversation_id,
            )
            .first()
        )

        if existing:
            existing.brief = brief
            db.session.commit()
            return existing

        record = ConversationBrief(
            tenant_id=app_model.tenant_id,
            app_id=app_model.id,
            user_id=user_id,
            conversation_id=conversation_id,
            brief=brief,
        )
        db.session.add(record)
        db.session.commit()
        return record

    @classmethod
    def search(
        cls,
        app_model: App,
        user_id: str | None,
        user_ids: str | None,
        sort_by: str,
        page: int,
        limit: int,
    ) -> dict[str, Any]:
        sort_field, sort_dir = cls._parse_sort(sort_by)

        stmt = select(ConversationBrief).where(
            ConversationBrief.tenant_id == app_model.tenant_id,
            ConversationBrief.app_id == app_model.id,
        )
        if user_id:
            stmt = stmt.where(ConversationBrief.user_id == user_id)
        elif user_ids:
            id_list = [i.strip() for i in user_ids.split(",") if i.strip()]
            if id_list:
                stmt = stmt.where(ConversationBrief.user_id.in_(id_list))

        total = db.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0

        page = max(page, 1)
        limit = max(limit, 1)
        offset = (page - 1) * limit

        rows = (
            db.session.scalars(stmt.order_by(sort_dir(getattr(ConversationBrief, sort_field))).offset(offset).limit(limit))
            .all()
        )
        # build nickname mapping
        user_ids = {row.user_id for row in rows}
        nick_map: dict[str, str | None] = {}
        if user_ids:
            nick_rows = (
                db.session.query(PatientProfile.end_user_id, PatientProfile.nickname)
                .filter(PatientProfile.end_user_id.in_(user_ids))
                .all()
            )
            nick_map = {uid: nick for uid, nick in nick_rows}

        data: list[dict[str, Any]] = []
        for row in rows:
            item = {
                "id": row.id,
                "tenant_id": row.tenant_id,
                "app_id": row.app_id,
                "user_id": row.user_id,
                "conversation_id": row.conversation_id,
                "brief": row.brief,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
                "nickname": nick_map.get(row.user_id),
            }
            data.append(item)
        has_more = offset + len(rows) < total

        return {
            "data": data,
            "page": page,
            "limit": limit,
            "total": total,
            "has_more": has_more,
        }

    @staticmethod
    def _parse_sort(sort_by: str):
        if sort_by == "updated_at":
            return "updated_at", asc
        if sort_by == "-updated_at":
            return "updated_at", desc
        if sort_by == "created_at":
            return "created_at", asc
        if sort_by == "-created_at":
            return "created_at", desc
        return "updated_at", desc
