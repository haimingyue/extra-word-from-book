# Backend

FastAPI backend skeleton for the book vocabulary analysis product.

当前书籍上传支持 `EPUB` 与“纯英文正文文本” `TXT` 两种格式。`TXT` 仅适用于纯正文场景，不保证带标记、表格或复杂元数据的文本文件效果。

## Quick Start

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e .
alembic upgrade head
uvicorn app.main:app --reload
```

## Key Environment Variables

- `APP_ENABLE_ANALYSIS_RESULT_ITEMS=true`

将其设置为 `false` 后，新分析任务会停止写入 `analysis_result_items`，但不会影响汇总结果与 CSV 下载。

## Auth

Current APIs (except `/auth/*`) require:

`Authorization: Bearer <access_token>`

Get the token from:
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`

## Response Shape

All JSON business APIs return:

```json
{
  "code": "OK",
  "message": "success",
  "data": {}
}
```

File download endpoints return the file stream directly.

## Database Migrations

Create or update the database schema with Alembic:

```bash
alembic upgrade head
```

If you already have an existing local `app.db` that was created before Alembic:

```bash
alembic stamp head
```

Use `stamp head` only once to mark the current schema as the initial baseline without re-running table creation.

Create a new migration after model changes:

```bash
alembic revision --autogenerate -m "describe change"
```

Rollback one migration:

```bash
alembic downgrade -1
```

## Structure

- `app/main.py`: application entrypoint
- `app/api/`: route registration
- `app/core/`: settings and shared configuration
- `app/db/`: database base and session
- `app/models/`: ORM models
- `app/schemas/`: request and response schemas
- `app/services/`: business services
- `app/pipeline/`: internal analysis pipeline stages
