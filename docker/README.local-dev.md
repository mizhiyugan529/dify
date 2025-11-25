# 本地 Docker 覆盖使用指南

仓库中 `docker/docker-compose.yaml` 是自动生成的，默认拉取官方镜像。要让 Docker 运行当前仓库里的 API 代码，请保持该文件不变，在它之上额外叠加 `docker/docker-compose.override.local.yaml`。

## API / Worker 使用本地源码

1. 在docker目录执行构建（首次或代码有变更时都需要）：
   ```bash
     docker compose \
     -f docker-compose.yaml \
     -f docker-compose.override.local.yaml \
     build api
   ```
   override 文件把 `api` 的 `context` 定向到 `../api`，构建出的镜像标记为 `dify-api:local`，`worker` 与 `worker_beat` 会直接复用这个 tag。同时它在三个服务里挂载了：
   - `./volumes/app/storage:/app/api/storage`：沿用原有存储。
   - `../api:/app/api`：让容器实时读取你本地源码。
   - `dify_api_venv:/app/api/.venv`：把镜像内置的虚拟环境保存在 Named Volume，下次启动不会被宿主机覆盖，避免出现 `flask: command not found`。
2. 启动整个栈：
   ```bash
   docker compose \
     -f docker-compose.yaml \
     -f docker-compose.override.local.yaml \
     up
   ```
   也可以在 `up` 命令后加 `-d` 后台运行，或使用 `up --build` 省去手动 build。
3. 每次修改 API 源码后记得重新执行第 1 步，确保容器加载的是最新镜像。

> override 文件不会被 `docker/generate_docker_compose` 覆盖，所以可以放心与官方生成流程共存。

### 暴露本地 API

`api` 服务会把容器内的 `5001` 端口映射到宿主机 `EXPOSE_API_PORT`（默认同样是 5001）。本地调试/用 Postman 验证时直接访问：

```
http://localhost:5001/v1/service_api/...
```

如果端口冲突，可提前设置环境变量：

```bash
export EXPOSE_API_PORT=5100
docker compose -f docker/docker-compose.yaml -f docker/docker-compose.override.local.yaml up -d api
```

随后所有请求就可以打到 `http://localhost:5100`。

### 暴露数据库端口

`docker-compose.override.local.yaml` 已额外挂载 `db` 服务的 `5432` 端口，默认映射为本机 `5432`。需要修改时，先在环境变量里设置 `EXPOSE_POSTGRES_PORT`，例如：

```bash
export EXPOSE_POSTGRES_PORT=5543
docker compose -f docker/docker-compose.yaml -f docker/docker-compose.override.local.yaml up -d db
```

随后即可使用 `psql postgresql://postgres:difyai123456@localhost:5543/dify` 或任意 GUI 工具连接并查看数据库。

### Web 容器的 PM2 日志

`web` 服务将 `PM2_HOME` 指向容器内 `/tmp/.pm2`（不再挂载宿主机/卷）。若之前的挂载导致 socket 报错（EINVAL/ENOTSUP），请清理后重启：

```bash
cd docker
docker compose -f docker-compose.yaml -f docker-compose.override.local.yaml down -v
docker compose -f docker-compose.yaml -f docker-compose.override.local.yaml up -d web
```

PM2 会在容器内部写入 logs/pids，避免 ENOENT/EINVAL/EACCES 问题。

## 自定义接口汇总（Postman 可直接调用）

调用地址：
- 直连 API 容器：`http://localhost:${EXPOSE_API_PORT:-5001}/v1/...`
- 经 Nginx 网关：`http://localhost:12380/api/v1/...`
  > 路径无需 `service_api` 前缀，蓝图前缀就是 `/v1`，Nginx 只加了 `/api`。

- `PUT /v1/conversations/<conversation_id>/consultation-brief`：更新首条消息的简介（存储于 `messages.consultation_brief`）。
- `PUT /v1/messages/<message_id>/consultation-brief`：直接更新任意消息的简介字段。
- `GET /v1/messages/search-advanced?conversation_id=&end_user_id=&start_time=&end_time=&keyword=&has_consultation_brief=&page=&limit=`：按时间/会话/关键词检索消息，关键词匹配 query/answer/consultation_brief，可选 `end_user_id` 过滤；留空则不限制用户。
- `GET /v1/conversations/search?end_user_id=&start_time=&end_time=&keyword=&page=&limit=&sort_by=`：按用户/时间/关键词检索会话，关键词匹配名称/summary/首条消息简介。
- `GET /v1/patients/<user_id>/profile`：根据自定义用户ID（字符串）查询患者档案。
- `PUT /v1/patients/<user_id>/profile`：更新患者档案（字段：`nickname`、`emotion`、`compliance`、`communication_style`、`health_behavior`，均可选）。
- `GET /v1/patients/search?user_id=&user_ids=&nickname=&emotion=&compliance=&communication_style=&health_behavior=&page=&limit=&sort_by=`：分页检索患者，支持按单个/列表用户ID、昵称模糊及各字段精确过滤。
- `PUT /v1/briefs`：写入/更新会话简介，字段：`user_id`（字符串）、`conversation_id`、`brief`。
- `GET /v1/briefs?user_id=&sort_by=&page=&limit=`：按更新时间/创建时间排序检索简介，可选按 `user_id` 过滤，返回包含患者昵称。
- `GET /v1/stats/summary`：今日对话数、总对话数、较前日增量（取昨天减前天）、情绪为焦虑/紧张/恐惧的患者数量及 ID 列表、今日新增档案数、brief 词频统计（同时落表 `daily_app_stats`）。

## 数据库与中间件

Compose 配置已经包含 `db`（PostgreSQL）、`redis` 以及沙箱等中间件：

- 直接使用上面的组合命令 (`docker compose ... up`) 就会同时启动 API、Worker 和所有依赖。
- 如果只想起中间件、在本地 `uv run` 运行 API，可以使用：
  ```bash
  make prepare-docker
  ```
  该命令会自动复制 `docker/middleware.env`（若不存在）并执行：
  ```bash
  cd docker && docker compose \
    -f docker-compose.middleware.yaml \
    --env-file middleware.env \
    -p dify-middlewares-dev \
    up -d
  ```
  如需清理/停止这些容器，运行 `make dev-clean`。

通过以上方式即可在 Docker 中运行 PostgreSQL、Redis 等服务，同时通过 override 让 API/Worker 镜像始终来自本地源码。
