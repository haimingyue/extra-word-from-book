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
```

编辑 `/srv/extra-word-from-book/env/frontend.env`：

```env
NUXT_PUBLIC_API_BASE=http://你的域名/api/v1
```

## 4. 启动服务

```bash
docker compose up -d --build
```

查看状态：

```bash
docker compose ps
docker compose logs -f backend
```

## 5. 更新代码

后续发布新版本时：

```bash
cd /srv/extra-word-from-book/app
git pull
docker compose up -d --build
```

如果服务器内存较小，前端更新建议改为分步执行，先停止当前项目的 `backend/frontend/nginx`，再单独构建前端，避免构建时资源峰值过高：

```bash
cd /srv/extra-word-from-book/app
git pull
docker compose stop backend frontend nginx
docker compose build frontend
docker compose up -d backend frontend nginx
```

如果前端发布完成后还需要再发布后端，可继续执行：

```bash
docker compose build backend
docker compose up -d backend
```

## 6. 说明

- 当前 `backend` 容器启动时会自动执行 `alembic upgrade head`。
- 当前仅开放 `80` 端口；如需 HTTPS，建议再接入 `certbot` 或云厂商负载均衡。
- 2C2G 机器建议先控制分析并发，避免同时跑多个大文件任务。
