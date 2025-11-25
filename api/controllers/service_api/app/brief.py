from flask_restx import Resource, reqparse

from controllers.service_api import service_api_ns
from controllers.service_api.wraps import FetchUserArg, WhereisUserArg, validate_app_token
from fields.brief_fields import build_brief_model, build_brief_search_model
from libs.helper import uuid_value
from models.model import App, EndUser
from services.brief_service import BriefService


brief_upsert_parser = (
    reqparse.RequestParser()
    .add_argument("user_id", type=str, required=True, location="json", help="自定义用户ID")
    .add_argument("conversation_id", type=uuid_value, required=True, location="json", help="会话ID")
    .add_argument("brief", type=str, required=True, location="json", help="简介内容")
)

brief_search_parser = (
    reqparse.RequestParser()
    .add_argument("user_id", type=str, location="args", help="自定义用户ID，可选")
    .add_argument("user_ids", type=str, location="args", help="逗号分隔的用户ID列表")
    .add_argument(
        "sort_by",
        type=str,
        choices=["updated_at", "-updated_at", "created_at", "-created_at"],
        default="-updated_at",
        location="args",
        help="按更新时间/创建时间排序",
    )
    .add_argument("page", type=int, default=1, location="args", help="页码")
    .add_argument("limit", type=int, default=20, location="args", help="每页数量")
)


@service_api_ns.route("/briefs")
class ConversationBriefApi(Resource):
    @service_api_ns.expect(brief_upsert_parser)
    @service_api_ns.doc("upsert_conversation_brief")
    @service_api_ns.marshal_with(build_brief_model(service_api_ns))
    @validate_app_token(fetch_user_arg=FetchUserArg(fetch_from=WhereisUserArg.JSON))
    def put(self, app_model: App, end_user: EndUser | None):
        args = brief_upsert_parser.parse_args()
        record = BriefService.upsert(
            app_model=app_model,
            user_id=args["user_id"],
            conversation_id=args["conversation_id"],
            brief=args["brief"],
        )
        return record

    @service_api_ns.expect(brief_search_parser)
    @service_api_ns.doc("search_conversation_brief")
    @service_api_ns.marshal_with(build_brief_search_model(service_api_ns))
    @validate_app_token(fetch_user_arg=FetchUserArg(fetch_from=WhereisUserArg.QUERY))
    def get(self, app_model: App, end_user: EndUser | None):
        args = brief_search_parser.parse_args()
        return BriefService.search(
            app_model=app_model,
            user_id=args["user_id"],
            user_ids=args["user_ids"],
            sort_by=args["sort_by"],
            page=args["page"],
            limit=args["limit"],
        )
