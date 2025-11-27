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
- `GET /v1/patients/search?user_id=&user_ids=&nickname=&emotion=&compliance=&communication_style=&health_behavior=&month=&page=&limit=&sort_by=`：分页检索患者，支持按单个/列表用户ID、昵称模糊及各字段精确过滤，`emotion` 支持多选（逗号分隔，包含“平静”时会同时返回 emotion 为空的档案），`month` 为创建年月（YYYYMM，例如 202511）。
- `PUT /v1/briefs`：写入/更新会话简介，字段：`user_id`（字符串）、`conversation_id`、`brief`。
- `GET /v1/briefs?user_id=&sort_by=&page=&limit=`：按更新时间/创建时间排序检索简介，可选按 `user_id` 过滤，返回包含患者昵称。
- `GET /v1/stats/summary`：对话与患者情绪月度概览（见下文接口详情）。

### 接口详情：GET /v1/stats/summary

- 作用：获取当前 App 的月度/累计对话量、月环比、情绪告警（焦虑/恐惧）、简要词频，以及全部情绪分布；同时把当天数据写入 `daily_app_stats`（含情绪分布字段）。
- 鉴权：`Authorization: Bearer <app-token>`，可选 `end_user` 查询参数沿用现有校验。
- 返回字段说明：
  - `total_conversations`：历史累计对话数。
  - `current_month_conversations`：本月迄今对话数（当月 1 日 00:00 至明日 00:00，含当日）。
  - `last_month_conversations`：上月同期对话数（上月 1 日 00:00 起，长度与本月迄今一致，最多不超过上月结束）。
  - `conversation_month_over_month_rate`：本月迄今对比上月同期的环比增幅，`(本月迄今-上月同期)/上月同期`，上月同期为 0 时返回 0。
  - `emotion_alert_count`：本月迄今情绪为焦虑/恐惧/紧张的患者总数（按患者档案创建时间筛选）。
  - `emotion_alert_user_ids`：本月迄今最新的告警患者 ID 列表（最多 3 个）。
  - `new_profiles_current_month`：本月新增患者档案数。
  - `brief_summary`：会话简介的词频统计，过滤空值与“其他”。
  - `emotion_distribution`：全部患者情绪分布，含 `calm | anxious | tense | confused | fearful`（对应 平静 / 焦虑 / 紧张 / 迷茫 / 恐惧），未填/未知视为 `calm`。
- 典型响应：
  ```json
  {
    "total_conversations": 1200,
    "current_month_conversations": 300,
    "last_month_conversations": 250,
    "conversation_month_over_month_rate": 0.2,
    "emotion_alert_count": 8,
    "emotion_alert_user_ids": ["u_3", "u_2", "u_1"],
    "new_profiles_current_month": 42,
    "brief_summary": {"甲状腺": 10, "心血管": 6},
    "emotion_distribution": {
      "calm": 90,
      "anxious": 8,
      "tense": 3,
      "confused": 4,
      "fearful": 5
    }
  }
  ```

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

## 打包 API 源码（Linux）并在服务器使用

下面的流程让你在本地打一个 API 源码压缩包（Linux `tar`），然后在服务器解压并让 `api`/`worker`/`worker_beat` 使用你的源码。

### 本地打包（Linux）

在项目根目录执行（确保在 Linux 环境下使用系统自带 `tar`）：

```bash
# 打包 api 目录，排除常见缓存/虚拟环境/构建产物
tar --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='.mypy_cache' \
    --exclude='.pytest_cache' \
    --exclude='storage' \
    -czf dify-api-src.tar.gz api
```

生成的 `dify-api-src.tar.gz` 即可传到服务器（如 `scp dify-api-src.tar.gz user@server:/opt/dify/`）。

### 服务器侧落地并启用

```bash
cd /opt/dify
mkdir -p api-src
tar -xzf dify-api-src.tar.gz -C api-src

# 构建使用本地源码的镜像
cd docker
docker compose \
  -f docker-compose.yaml \
  -f docker-compose.override.local.yaml \
  build api

# 以源码挂载+新镜像启动（如需后台加 -d）
docker compose \
  -f docker-compose.yaml \
  -f docker-compose.override.local.yaml \
  up api worker worker_beat
```

说明：
- 上述 `build api` 会读取 `docker-compose.override.local.yaml` 中的 `context: ../api`，因此确保解压后的目录结构与仓库一致（`/opt/dify/api-src/api`）。
- 如需固定使用解压目录，可在 override 文件中将 `../api` 改为绝对路径（例如 `/opt/dify/api-src/api`），再执行 build/up。
- `worker` 与 `worker_beat` 会复用同一个 `dify-api:local` 镜像和源码挂载，无需额外调整。

## 在本地用 linux/amd64 架构构建并打包 Docker 目录

如果服务器是 Linux/amd64，建议在本地直接用 linux/amd64 平台构建镜像，再打包 `docker` 目录上传。

### 1）本地设置平台并构建（Linux）

```bash
# 确保在 Linux 环境，并将默认构建平台切为 linux/amd64
export DOCKER_DEFAULT_PLATFORM=linux/amd64

cd docker
docker compose \
  -f docker-compose.yaml \
  -f docker-compose.override.local.yaml \
  build api
```

说明：
- 设置 `DOCKER_DEFAULT_PLATFORM` 后，`api`、`worker`、`worker_beat` 的镜像都会以 linux/amd64 架构构建。
- 如果你修改了 `docker-compose.override.local.yaml` 中的挂载目录（例如改成绝对路径），确保服务器目录结构匹配。

### 2）打包 Docker 目录上传

在项目根目录执行（仍在 Linux 环境）：

```bash
tar -czf docker-bundle.tar.gz docker
```

将 `docker-bundle.tar.gz` 上传到服务器目标目录（例如 `/opt/dify/`）。

### 3）服务器解压并启动

```bash
cd /opt/dify
tar -xzf docker-bundle.tar.gz

# 确保有源码：如果按前文已上传 api 源码包，也解压到 /opt/dify/api-src

cd docker
export DOCKER_DEFAULT_PLATFORM=linux/amd64
docker compose \
  -f docker-compose.yaml \
  -f docker-compose.override.local.yaml \
  up -d api worker worker_beat
```

如果需要变更挂载目录（例如 `/opt/dify/api-src/api`），直接编辑 `docker-compose.override.local.yaml` 的 `api/worker/worker_beat` 三个服务的 `context` 与 `volumes` 路径，再执行 `docker compose build api` 与 `docker compose up ...`。

## 只打包/传输 API 镜像（不带其他容器）

如果服务器上只需要更新 API 镜像（`worker` 仍可复用官方镜像或不用），可以在本地按以下步骤操作：

```bash
# 1) 仍推荐设置平台确保与服务器一致
export DOCKER_DEFAULT_PLATFORM=linux/amd64

# 可选：若构建时出现 debian GPG 签名错误，可提前换 https 镜像源
# export DEBIAN_MIRROR=https://mirrors.aliyun.com/debian
# export DEBIAN_SECURITY_MIRROR=https://mirrors.aliyun.com/debian-security

# 2) 在 docker 目录仅构建 api 镜像（如切源则带上 build-arg）
cd docker
docker compose \
  -f docker-compose.yaml \
  -f docker-compose.override.local.yaml \
  build \
  --build-arg DEBIAN_MIRROR=${DEBIAN_MIRROR:-https://deb.debian.org/debian} \
  --build-arg DEBIAN_SECURITY_MIRROR=${DEBIAN_SECURITY_MIRROR:-https://deb.debian.org/debian-security} \
  api

# 3) 导出镜像为 tar（只含 api）
docker save -o dify-api-linux-amd64.tar dify-api:local

# 4) 将 tar 传到服务器，例如
scp dify-api-linux-amd64.tar user@server:/opt/dify/
```

服务器侧加载并运行：

```bash
cd /opt/dify
docker load -i dify-api-linux-amd64.tar

# 如仅启动 API：
cd docker
export DOCKER_DEFAULT_PLATFORM=linux/amd64
docker compose \
  -f docker-compose.yaml \
  -f docker-compose.override.local.yaml \
  up -d api
```

说明：
- `docker-compose.override.local.yaml` 会挂载源码目录；若服务器端没有对应目录或你不打算挂载源码，可暂时从 override 中移除 `volumes`/`context`，改用镜像内置代码。
- 若想 `worker` 也使用这份镜像，可在服务器加载后执行 `docker compose ... up -d api worker worker_beat`，它们会复用 `dify-api:local`。
