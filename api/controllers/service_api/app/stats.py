from flask_restx import Resource

from controllers.service_api import service_api_ns
from controllers.service_api.wraps import FetchUserArg, WhereisUserArg, validate_app_token
from fields.stats_fields import build_stats_summary_model
from models.model import App, EndUser
from services.stats_service import StatsService


@service_api_ns.route("/stats/summary")
class StatsSummaryApi(Resource):
    @service_api_ns.marshal_with(build_stats_summary_model(service_api_ns))
    @validate_app_token(fetch_user_arg=FetchUserArg(fetch_from=WhereisUserArg.QUERY))
    def get(self, app_model: App, end_user: EndUser | None):
        return StatsService.summary(app_model)
