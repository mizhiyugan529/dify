from flask_restx import Api, Namespace, fields


stats_summary_fields = {
    "total_conversations": fields.Integer,
    "today_conversations": fields.Integer,
    "conversation_delta_vs_previous": fields.Integer,
    "emotion_alert_count": fields.Integer,
    "emotion_alert_user_ids": fields.List(fields.String),
    "new_profiles_today": fields.Integer,
    "brief_summary": fields.Raw,
}


def build_stats_summary_model(api_or_ns: Api | Namespace):
    return api_or_ns.model("StatsSummary", stats_summary_fields)
