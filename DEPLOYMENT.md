# Docker 部署说明

## 目录规划

服务器建议使用以下目录结构：

```text
/srv/extra-word-from-book/
  app/                     # git clone 下来的代码仓库
  data/
    postgres/              # PostgreSQL 数据目录
    storage/               # 上传书籍与导出结果
    dicts/
      ecdict.csv
      词根词缀记单词.csv
  env/
    backend.env
    frontend.env
```

以下示例默认你在 `/srv/extra-word-from-book/app` 下执行。

## 1. 准备目录

```bash
mkdir -p /srv/extra-word-from-book/{app,data/postgres,data/storage,data/dicts,env}
```

把两个词典文件放到：

```text
/srv/extra-word-from-book/data/dicts/ecdict.csv
/srv/extra-word-from-book/data/dicts/词根词缀记单词.csv
```

## 2. 上传代码

推荐使用 Git：

```bash
cd /srv/extra-word-from-book
git clone <你的仓库地址> app
cd app
```

## 3. 配置环境变量

复制示例文件：

```bash
cp .env.example .env
cp backend/.env.example /srv/extra-word-from-book/env/backend.env
cp frontend/.env.example /srv/extra-word-from-book/env/frontend.env
```

编辑 `/srv/extra-word-from-book/app/.env`：

```env
POSTGRES_DB=extra_word
POSTGRES_USER=extra_word
POSTGRES_PASSWORD=替换成强密码
```

编辑 `/srv/extra-word-from-book/env/backend.env`：

```env
APP_DATABASE_URL=postgresql+psycopg://extra_word:替换成强密码@postgres:5432/extra_word
APP_STORAGE_ROOT=/data/storage
APP_ECDICT_PATH=/data/dicts/ecdict.csv
APP_COCA_WORDS_PATH=/data/dicts/词根词缀记单词.csv
APP_CORS_ORIGINS=http://你的域名,http://服务器公网IP
APP_JWT_SECRET_KEY=替换成长随机字符串
APP_BOOK_UPLOAD_MAX_SIZE_MB=100
```

编辑 `/srv/extra-word-from-book/env/frontend.env`：

```env
NUXT_PUBLIC_API_BASE=http://你的域名/api/v1
```

## 4. 首次启动

```bash
docker compose up -d --build
```

查看状态：

```bash
docker compose ps
docker compose logs -f backend
```

建议继续确认前后端都真正处于运行态：

```bash
docker compose ps
docker compose logs --tail=50 frontend
docker compose logs --tail=50 nginx
```

预期结果：

- `backend` 状态为 `Up`
- `frontend` 状态为 `Up`
- `nginx` 状态为 `Up`
- `frontend` 日志出现 `Listening on http://0.0.0.0:3000`

如果只看到 `backend` 运行，而 `frontend` 或 `nginx` 是 `Exited`，先执行：

```bash
docker compose up -d frontend nginx
docker compose ps
```

上传 `EPUB` 前，还要确认所有入口层的请求体限制一致，至少不要小于 `APP_BOOK_UPLOAD_MAX_SIZE_MB`。当前仓库内应用 `nginx` 默认是 `100m`，如果你的公网入口前面还有额外的 `gateway-nginx`、云负载均衡或 CDN，也必须同步放开；否则公网请求会直接返回 `413`，请求到不了应用。

项目内 `nginx` 配置位于 [deploy/nginx.conf](/Users/simoonqian/Desktop/extra-word-from-book/deploy/nginx.conf:1)，当前默认：

```nginx
client_max_body_size 100m;
```

## 5. 更新代码

后续发布新版本时：

```bash
cd /srv/extra-word-from-book/app
git pull
docker compose up -d --build
```

如果服务器内存较小，前端更新建议改为分步执行，先停止当前项目的 `backend/frontend/nginx`，再单独构建前端，避免构建时资源峰值过高。`1.6G` 左右的小机器上，前端构建可能在 `rendering chunks` 或 `Building Nuxt Nitro server` 阶段耗时较久：

```bash
cd /srv/extra-word-from-book/app
git pull
docker compose stop backend frontend nginx
docker compose build frontend
docker compose up -d backend frontend nginx
```

```bash
cd /srv/extra-word-from-book/app
git pull
docker compose stop backend nginx
docker compose build backend
docker compose up -d backend nginx
```


如果只需要重启服务而不重建镜像：

```bash
cd /srv/extra-word-from-book/app
docker compose up -d backend frontend nginx
docker compose ps
```

## 6. 数据库迁移校验

当前 `backend` 容器启动时会自动执行 `alembic upgrade head`，但仍建议在发布后手工检查一次：

```bash
docker compose exec backend alembic current
docker compose exec backend alembic upgrade head
```

对于已存在的老库，建议额外确认 `analysis_jobs` 表结构：

```bash
docker compose exec postgres psql -U extra_word -d extra_word -c "\d analysis_jobs"
```

至少应包含以下字段：

- `known_words_level`
- `known_words_mode`
- `known_words_value`

如果 `alembic current` 已显示最新版本，但 `analysis_jobs` 缺少 `known_words_mode` 或 `known_words_value`，说明迁移记录和真实 schema 不一致。可以先手动补列，再继续发布：

```bash
docker compose exec postgres psql -U extra_word -d extra_word -c "
ALTER TABLE analysis_jobs
ADD COLUMN IF NOT EXISTS known_words_mode VARCHAR(20) DEFAULT 'coca_rank',
ADD COLUMN IF NOT EXISTS known_words_value VARCHAR(20) DEFAULT '3000';
UPDATE analysis_jobs
SET known_words_mode = COALESCE(known_words_mode, 'coca_rank'),
    known_words_value = COALESCE(known_words_value, CAST(known_words_level AS VARCHAR), '3000');
ALTER TABLE analysis_jobs
ALTER COLUMN known_words_mode SET NOT NULL,
ALTER COLUMN known_words_value SET NOT NULL;
CREATE INDEX IF NOT EXISTS ix_analysis_jobs_known_words_mode ON analysis_jobs (known_words_mode);
"
```

完成后再重新验证：

```bash
docker compose exec postgres psql -U extra_word -d extra_word -c "\d analysis_jobs"
```

## 7. 常见排查

- 登录正常、上传正常，但分析时报 `500`：
  通常先看 `backend` 日志，重点排查数据库缺列、书籍文件路径错误、词典文件缺失。

```bash
docker compose logs backend --tail=200
```

- 页面访问返回 `502`：
  通常是 `frontend` 或 `nginx` 没起来，先看容器状态。

```bash
docker compose ps -a
docker compose up -d frontend nginx
docker compose logs --tail=100 frontend
docker compose logs --tail=100 nginx
```

- `POST /api/v1/analysis/jobs` 返回 `422`：
  先在浏览器开发者工具里检查 `Payload` 和 `Response`，确认前端实际发送了哪些字段。

- 当前仅开放 `80` 端口；如需 HTTPS，建议再接入 `certbot` 或云厂商负载均衡。
- 2C2G 机器建议先控制分析并发，避免同时跑多个大文件任务。
