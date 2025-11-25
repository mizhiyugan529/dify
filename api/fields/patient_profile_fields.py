from flask_restx import Api, Namespace, fields

from libs.helper import TimestampField

patient_profile_fields = {
    "id": fields.String,
    "tenant_id": fields.String,
    "app_id": fields.String,
    "end_user_id": fields.String,
    "nickname": fields.String,
    "emotion": fields.String,
    "compliance": fields.String,
    "communication_style": fields.String,
    "health_behavior": fields.String,
    "latest_brief": fields.String,
    "latest_brief_conversation_id": fields.String,
    "created_at": TimestampField,
    "updated_at": TimestampField,
}


def build_patient_profile_model(api_or_ns: Api | Namespace):
    return api_or_ns.model("PatientProfile", patient_profile_fields)


def build_patient_profile_response_model(api_or_ns: Api | Namespace):
    profile_model = build_patient_profile_model(api_or_ns)
    return api_or_ns.model(
        "PatientProfileResponse",
        {
            "profile": fields.Nested(profile_model, allow_null=True),
            # for search pagination
            "data": fields.List(fields.Nested(profile_model), default=[]),
            "page": fields.Integer,
            "limit": fields.Integer,
            "total": fields.Integer,
            "has_more": fields.Boolean,
        },
    )
