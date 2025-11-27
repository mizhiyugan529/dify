from flask_restx import Resource, reqparse
from controllers.service_api import service_api_ns
from controllers.service_api.wraps import FetchUserArg, WhereisUserArg, validate_app_token
from fields.patient_profile_fields import build_patient_profile_response_model
from models.model import App, EndUser
from services.patient_profile_service import PatientProfileService

profile_parser = (
    reqparse.RequestParser()
    .add_argument("emotion", type=str, location="json", help="情绪")
    .add_argument("compliance", type=str, location="json", help="配合度")
    .add_argument("communication_style", type=str, location="json", help="交流风格")
    .add_argument("health_behavior", type=str, location="json", help="健康管理倾向")
    .add_argument("nickname", type=str, location="json", help="昵称")
)


@service_api_ns.route("/patients/<string:user_id>/profile")
class PatientProfileApi(Resource):
    @service_api_ns.expect(profile_parser)
    @service_api_ns.doc("upsert_patient_profile")
    @service_api_ns.doc(description="新增或更新患者档案信息")
    @service_api_ns.doc(params={"user_id": "自定义用户 ID（字符串）"})
    @validate_app_token(fetch_user_arg=FetchUserArg(fetch_from=WhereisUserArg.JSON))
    @service_api_ns.marshal_with(build_patient_profile_response_model(service_api_ns))
    def put(self, app_model: App, end_user: EndUser, user_id):
        profile = PatientProfileService.upsert(app_model, str(user_id), profile_parser.parse_args())
        return {"profile": profile}

    @service_api_ns.doc("get_patient_profile")
    @service_api_ns.doc(description="查询患者档案信息")
    @service_api_ns.doc(params={"user_id": "自定义用户 ID（字符串）"})
    @validate_app_token(fetch_user_arg=FetchUserArg(fetch_from=WhereisUserArg.QUERY))
    @service_api_ns.marshal_with(build_patient_profile_response_model(service_api_ns))
    def get(self, app_model: App, end_user: EndUser, user_id):
        profile = PatientProfileService.get_or_none(app_model, str(user_id))
        return {"profile": profile}


search_parser = (
    reqparse.RequestParser()
    .add_argument("user_ids", type=str, location="args", help="逗号分隔的用户ID列表")
    .add_argument("user_id", type=str, location="args", help="单个用户ID精确匹配")
    .add_argument("nickname", type=str, location="args", help="昵称模糊匹配")
    .add_argument("emotion", type=str, location="args", help="情绪精确匹配，可多选逗号分隔")
    .add_argument("compliance", type=str, location="args", help="配合度精确匹配")
    .add_argument("communication_style", type=str, location="args", help="交流风格精确匹配")
    .add_argument("health_behavior", type=str, location="args", help="健康管理倾向精确匹配")
    .add_argument("month", type=str, location="args", help="按创建年月筛选，格式 YYYYMM，如 202511")
    .add_argument("page", type=int, default=1, location="args")
    .add_argument("limit", type=int, default=20, location="args")
    .add_argument(
        "sort_by",
        type=str,
        choices=["updated_at", "-updated_at", "created_at", "-created_at"],
        default="-updated_at",
        location="args",
    )
)


@service_api_ns.route("/patients/search")
class PatientProfileSearchApi(Resource):
    @service_api_ns.expect(search_parser)
    @service_api_ns.marshal_with(build_patient_profile_response_model(service_api_ns))
    @validate_app_token(fetch_user_arg=FetchUserArg(fetch_from=WhereisUserArg.QUERY))
    def get(self, app_model: App, end_user: EndUser | None):
        args = search_parser.parse_args()
        profiles = PatientProfileService.search(
            app_model=app_model,
            user_id=args["user_id"],
            user_ids=args["user_ids"],
            nickname=args["nickname"],
            emotion=args["emotion"],
            compliance=args["compliance"],
            communication_style=args["communication_style"],
            health_behavior=args["health_behavior"],
            month=args["month"],
            page=args["page"],
            limit=args["limit"],
            sort_by=args["sort_by"],
        )
        return profiles
