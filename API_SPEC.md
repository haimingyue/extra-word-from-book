# API SPEC

## 1. 目标

本接口规范服务于英文书籍词汇分析产品的 MVP 版本，覆盖以下核心能力：
- 用户注册与登录
- 书籍上传与去重
- 异步分析任务创建与查询
- 分析结果查询与 CSV 下载
- 用户个人词库上传与管理
- 历史记录查询与删除

接口风格以 `REST` 为主，返回 `JSON`。文件上传使用 `multipart/form-data`。认证方式采用基于 Token 的鉴权。

## 2. 通用约定

### 2.1 Base URL
- 开发环境：`/api/v1`

### 2.2 认证
- 除注册、登录接口外，其他接口均需要认证
- 请求头：
  - `Authorization: Bearer <token>`

### 2.3 通用响应格式

成功响应：

```json
{
  "code": "OK",
  "message": "success",
  "data": {}
}
```

失败响应：

```json
{
  "code": "INVALID_REQUEST",
  "message": "request validation failed",
  "data": null
}
```

### 2.4 常用错误码
- `INVALID_REQUEST`
- `UNAUTHORIZED`
- `FORBIDDEN`
- `NOT_FOUND`
- `CONFLICT`
- `UNSUPPORTED_FORMAT`
- `PARSE_FAILED`
- `INTERNAL_ERROR`

## 3. 认证接口

### 3.1 注册
`POST /auth/register`

请求体：

```json
{
  "email": "user@example.com",
  "password": "string",
  "display_name": "string"
}
```

规则：
- `email` 必填且唯一
- `password` 必填
- MVP 不做邮箱验证

响应体：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "user_id": 1,
    "email": "user@example.com",
    "display_name": "Tom"
  }
}
```

### 3.2 登录
`POST /auth/login`

请求体：

```json
{
  "email": "user@example.com",
  "password": "string"
}
```

响应体：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "access_token": "jwt-or-token",
    "token_type": "Bearer",
    "user": {
      "user_id": 1,
      "email": "user@example.com",
      "display_name": "Tom"
    }
  }
}
```

## 4. 书籍接口

### 4.1 上传书籍
`POST /books/upload`

说明：
- 仅支持英文 `epub`
- 服务端需对文件做哈希去重
- 若书籍已存在，不重复存储文件，直接返回已存在书籍信息

请求类型：
- `multipart/form-data`

请求字段：
- `file`: 书籍文件

成功响应：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "book_id": 101,
    "original_filename": "Pride and Prejudice.epub",
    "title": "Pride and Prejudice",
    "language": "en",
    "is_duplicate": false
  }
}
```

重复书籍响应：

```json
{
  "code": "OK",
  "message": "book already exists",
  "data": {
    "book_id": 101,
    "original_filename": "Pride and Prejudice.epub",
    "title": "Pride and Prejudice",
    "language": "en",
    "is_duplicate": true
  }
}
```

失败场景：
- 非 `epub` 返回 `UNSUPPORTED_FORMAT`
- 非英文书籍返回 `UNSUPPORTED_FORMAT`
- 文件解析异常返回 `PARSE_FAILED`

### 4.2 历史记录 / 书架
`GET /books/history`

查询参数：
- `page`
- `page_size`
- `status` 可选

响应体：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "items": [
      {
        "result_id": 1001,
        "job_id": 901,
        "book_id": 101,
        "title": "Pride and Prejudice",
        "original_filename": "Pride and Prejudice.epub",
        "status": "completed",
        "known_words_mode": "coca_rank",
        "known_words_value": "3000",
        "to_memorize_word_count": 836,
        "created_at": "2026-03-20T10:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

## 5. 分析任务接口

### 5.1 创建分析任务
`POST /analysis/jobs`

说明：
- 对外为单接口
- 对内执行多阶段流水线
- 同一本书允许重复分析

请求体：

```json
{
  "book_id": 101,
  "known_words_mode": "exam_level",
  "known_words_value": "四级"
}
```

规则：
- `known_words_mode = exam_level` 时，`known_words_value` 必须为 `初中 / 高中 / 四级 / 六级` 之一
- `known_words_mode = coca_rank` 时，`known_words_value` 必须在 `1000..15000` 范围内
- 已掌握词 = 当前所选范围 + 当前用户主词库并集

响应体：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "job_id": 901,
    "book_id": 101,
    "status": "pending",
    "known_words_mode": "exam_level",
    "known_words_value": "四级"
  }
}
```

### 5.2 查询任务状态
`GET /analysis/jobs/{job_id}`

响应体：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "job_id": 901,
    "book_id": 101,
    "status": "processing",
    "known_words_mode": "exam_level",
    "known_words_value": "四级",
    "error_code": null,
    "error_message": null,
    "queued_at": "2026-03-20T10:00:00Z",
    "started_at": "2026-03-20T10:00:05Z",
    "finished_at": null,
    "result_id": null
  }
}
```

完成后：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "job_id": 901,
    "book_id": 101,
    "status": "completed",
    "known_words_mode": "exam_level",
    "known_words_value": "四级",
    "error_code": null,
    "error_message": null,
    "queued_at": "2026-03-20T10:00:00Z",
    "started_at": "2026-03-20T10:00:05Z",
    "finished_at": "2026-03-20T10:00:42Z",
    "result_id": 1001
  }
}
```

### 5.3 取消任务
`POST /analysis/jobs/{job_id}/cancel`

说明：
- 仅允许取消 `pending` 或可中断的 `processing` 任务

响应体：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "job_id": 901,
    "status": "canceled"
  }
}
```

## 6. 分析结果接口

### 6.1 查询分析结果
`GET /analysis/results/{result_id}`

响应体：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "result_id": 1001,
    "job_id": 901,
    "book": {
      "book_id": 101,
      "title": "Pride and Prejudice",
      "original_filename": "Pride and Prejudice.epub"
    },
    "summary": {
      "total_word_count": 78579,
      "unique_word_count": 5766,
      "to_memorize_word_count": 836,
      "coverage_95_word_count": 214
    },
    "reading_advice": {
      "level": "level_2",
      "label": "推荐阅读 + 学习",
      "color": "yellow",
      "message": "可以阅读，但建议先学习核心词表。"
    },
    "known_words_mode": "exam_level",
    "known_words_value": "四级",
    "created_at": "2026-03-20T10:00:42Z",
    "downloads": {
      "all_words": "/api/v1/analysis/results/1001/downloads/all_words",
      "to_memorize": "/api/v1/analysis/results/1001/downloads/to_memorize",
      "coverage_95": "/api/v1/analysis/results/1001/downloads/coverage_95"
    }
  }
}
```

字段语义补充：
- `coverage_95_word_count` 表示“在当前已掌握词基础上，为让全书累计覆盖率达到 `95%` 还需要补学的最小核心词数”
- `known_words_mode = exam_level` 时按词表 `Exam_Level` 过滤，并包含更低阶段的 `小学` 词；`known_words_mode = coca_rank` 时按 `COCA_Rank` 过滤

### 6.2 下载 CSV
`GET /analysis/results/{result_id}/downloads/{type}`

路径参数：
- `type`:
  - `all_words`
  - `to_memorize`
  - `coverage_95`

响应：
- 文件流下载
- `Content-Type: text/csv`

### 6.3 删除分析结果
`DELETE /analysis/results/{result_id}`

说明：
- 删除展示记录
- 删除结果文件
- 删除对应任务与结果元数据
- 若对应书籍无其他关联任务，可进一步触发书籍清理

响应体：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "result_id": 1001,
    "deleted": true
  }
}
```

## 7. 个人词库接口

### 7.1 获取词库列表
`GET /vocabularies`

响应体：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "items": [
      {
        "vocabulary_id": 301,
        "name": "My Main Vocabulary",
        "is_primary": true,
        "item_count": 1200,
        "created_at": "2026-03-20T08:00:00Z"
      }
    ]
  }
}
```

### 7.2 上传词表 TXT
`POST /vocabularies/upload`

请求类型：
- `multipart/form-data`

请求字段：
- `file`: `txt`
- `name`: 词表名称，可选
- `set_as_primary`: 是否设为主词库，可选

规则：
- 仅支持 `.txt`
- 兼容两种文本格式：
- `tab` 分隔导出格式，默认取第 2 列单词
- 一行一个英文单词格式
- 导入时按单词自动去重

响应体：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "vocabulary_id": 301,
    "name": "My Main Vocabulary",
    "imported_count": 1000,
    "deduplicated_count": 120
  }
}
```

失败场景：
- 文件格式错误返回 `UNSUPPORTED_FORMAT`

### 7.3 获取词表明细
`GET /vocabularies/{vocabulary_id}/items`

查询参数：
- `page`
- `page_size`
- `keyword` 可选

响应体：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "items": [
      {
        "item_id": 1,
        "word": "apple",
        "lemma": null
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

### 7.4 新增单词
`POST /vocabularies/items`

请求体：

```json
{
  "vocabulary_id": 301,
  "word": "apple"
}
```

规则：
- 按 `normalized_word` 去重
- 若已存在，可返回成功并标注未新增

响应体：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "item_id": 10001,
    "created": true
  }
}
```

### 7.5 删除单词
`DELETE /vocabularies/items/{item_id}`

响应体：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "item_id": 10001,
    "deleted": true
  }
}
```

## 8. 任务状态与轮询策略

前端在提交分析任务后，应轮询：
- `GET /analysis/jobs/{job_id}`

建议策略：
- 前 30 秒每 2 秒轮询一次
- 30 秒后每 5 秒轮询一次
- `completed` 后跳转结果页
- `failed` 后展示明确失败提示

## 9. 状态与错误语义

### 9.1 任务状态
- `pending`
- `processing`
- `completed`
- `failed`
- `canceled`

### 9.2 阅读等级
- `level_1`
- `level_2`
- `level_3`

### 9.3 任务错误码
- `unsupported_format`
- `parse_failed`

## 10. 权限规则

- 用户只能访问自己的词库
- 用户只能访问自己发起的分析任务
- 用户只能访问自己的分析结果与下载链接
- 用户不能删除其他用户的历史记录或词表数据

## 11. 非功能接口要求

- 上传接口应在数秒内完成响应，并返回 `book_id` 或去重结果
- 创建分析任务接口必须快速返回 `job_id`
- 下载接口应支持浏览器直接下载
- 所有列表接口应支持分页
- 所有删除接口应保持幂等，重复删除不应导致服务异常

## 12. 推荐实现顺序

建议按以下顺序实现：
1. `POST /auth/register`
2. `POST /auth/login`
3. `POST /books/upload`
4. `POST /vocabularies/upload`
5. `POST /analysis/jobs`
6. `GET /analysis/jobs/{job_id}`
7. `GET /analysis/results/{result_id}`
8. `GET /analysis/results/{result_id}/downloads/{type}`
9. `GET /books/history`
10. `DELETE /analysis/results/{result_id}`
