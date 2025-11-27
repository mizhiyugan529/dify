from flask_restx import Api, Namespace, fields


def build_stats_summary_model(api_or_ns: Api | Namespace):
    emotion_distribution_model = api_or_ns.model(
        "StatsEmotionDistribution",
        {
            "calm": fields.Integer,
            "anxious": fields.Integer,
            "tense": fields.Integer,
            "confused": fields.Integer,
            "fearful": fields.Integer,
        },
    )

    stats_summary_fields = {
        "total_conversations": fields.Integer,
        "current_month_conversations": fields.Integer,
        "last_month_conversations": fields.Integer,
        "conversation_month_over_month_rate": fields.Float,
        "emotion_alert_count": fields.Integer,
        "emotion_alert_user_ids": fields.List(fields.String),
        "new_profiles_current_month": fields.Integer,
        "brief_summary": fields.Raw,
        "emotion_distribution": fields.Nested(emotion_distribution_model),
    }

    return api_or_ns.model("StatsSummary", stats_summary_fields)
