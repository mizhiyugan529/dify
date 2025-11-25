from flask_restx import Api, Namespace, fields

from libs.helper import TimestampField


brief_fields = {
    "id": fields.String,
    "tenant_id": fields.String,
    "app_id": fields.String,
    "user_id": fields.String,
    "conversation_id": fields.String,
    "brief": fields.String,
    "created_at": TimestampField,
    "updated_at": TimestampField,
    "nickname": fields.String,
}


def build_brief_model(api_or_ns: Api | Namespace):
    return api_or_ns.model("ConversationBrief", brief_fields)


def build_brief_search_model(api_or_ns: Api | Namespace):
    brief_model = build_brief_model(api_or_ns)
    return api_or_ns.model(
        "ConversationBriefSearch",
        {
            "page": fields.Integer,
            "limit": fields.Integer,
            "total": fields.Integer,
            "has_more": fields.Boolean,
            "data": fields.List(fields.Nested(brief_model)),
        },
    )
