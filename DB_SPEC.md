# DB SPEC

## 1. 目标

本数据库设计服务于产品化的英文书籍词汇分析系统，必须支持以下能力：
- 用户注册与登录
- 用户个人词库管理
- 书籍去重与复用
- 异步分析任务
- 分析结果快照保存
- 三类 CSV 结果下载
- 同一本书按不同已掌握词范围重复分析

数据库只保存结构化数据、任务状态、统计结果和文件元数据。原始 `epub`、用户上传词表、导出 `csv` 应存放在对象存储或服务器文件存储中。

## 2. 设计原则

- 书籍与分析任务分离：一本书可对应多次分析
- 分析任务与分析结果分离：任务负责流程状态，结果负责快照与统计
- 用户词库与词条分离：底层支持多份词表，MVP 前端可展示为一份主词库
- 所有可复算的关键规则仍保留快照字段，避免历史结果被后续词库变更污染
- 使用文件哈希去重书籍

## 3. 核心表

### 3.1 `users`
用途：用户账户信息。

字段：
- `id` `bigint` PK
- `email` `varchar(255)` UNIQUE NOT NULL
- `password_hash` `varchar(255)` NOT NULL
- `display_name` `varchar(100)` NULL
- `status` `varchar(20)` NOT NULL DEFAULT `active`
- `created_at` `timestamp` NOT NULL
- `updated_at` `timestamp` NOT NULL
- `last_login_at` `timestamp` NULL

约束：
- 唯一索引：`email`

### 3.2 `user_vocabularies`
用途：用户词表集合。底层支持多份词表。

字段：
- `id` `bigint` PK
- `user_id` `bigint` FK -> `users.id`
- `name` `varchar(100)` NOT NULL
- `is_primary` `boolean` NOT NULL DEFAULT `false`
- `source_type` `varchar(20)` NOT NULL DEFAULT `manual`
- `source_file_key` `varchar(500)` NULL
- `item_count` `int` NOT NULL DEFAULT `0`
- `created_at` `timestamp` NOT NULL
- `updated_at` `timestamp` NOT NULL

建议枚举：
- `source_type`: `manual`, `txt_upload`

约束：
- 索引：`(user_id)`
- 可选唯一约束：每个用户仅允许一份 `is_primary = true` 的主词表

### 3.3 `user_vocabulary_items`
用途：用户词表中的单词明细。

字段：
- `id` `bigint` PK
- `vocabulary_id` `bigint` FK -> `user_vocabularies.id`
- `user_id` `bigint` FK -> `users.id`
- `word` `varchar(100)` NOT NULL
- `lemma` `varchar(100)` NULL
- `normalized_word` `varchar(100)` NOT NULL
- `created_at` `timestamp` NOT NULL

说明：
- `normalized_word` 用于大小写归一与去重，建议统一存小写。

约束：
- 唯一索引：`(vocabulary_id, normalized_word)`
- 索引：`(user_id, normalized_word)`

### 3.4 `books`
用途：去重后的书籍主记录。

字段：
- `id` `bigint` PK
- `file_hash` `varchar(128)` UNIQUE NOT NULL
- `original_filename` `varchar(255)` NOT NULL
- `title` `varchar(255)` NULL
- `language` `varchar(20)` NULL
- `file_size_bytes` `bigint` NULL
- `storage_key` `varchar(500)` NOT NULL
- `text_extract_status` `varchar(20)` NOT NULL DEFAULT `pending`
- `created_by_user_id` `bigint` FK -> `users.id`
- `created_at` `timestamp` NOT NULL
- `updated_at` `timestamp` NOT NULL

建议枚举：
- `text_extract_status`: `pending`, `ready`, `failed`

约束：
- 唯一索引：`file_hash`

### 3.5 `analysis_jobs`
用途：一次用户发起的异步分析任务。

字段：
- `id` `bigint` PK
- `user_id` `bigint` FK -> `users.id`
- `book_id` `bigint` FK -> `books.id`
- `status` `varchar(20)` NOT NULL DEFAULT `pending`
- `known_words_level` `int` NOT NULL
- `vocabulary_snapshot_count` `int` NOT NULL DEFAULT `0`
- `error_code` `varchar(50)` NULL
- `error_message` `varchar(500)` NULL
- `queued_at` `timestamp` NOT NULL
- `started_at` `timestamp` NULL
- `finished_at` `timestamp` NULL
- `created_at` `timestamp` NOT NULL
- `updated_at` `timestamp` NOT NULL

说明：
- `known_words_level` 取值范围为 `1000..15000`
- `vocabulary_snapshot_count` 表示发起任务时纳入并集的用户词条数量

建议枚举：
- `status`: `pending`, `processing`, `completed`, `failed`, `canceled`

约束：
- 索引：`(user_id, created_at DESC)`
- 索引：`(book_id, created_at DESC)`
- 索引：`(status, created_at)`

### 3.6 `analysis_job_vocabulary_snapshots`
用途：保存某次分析任务使用了哪些用户词条，保证结果快照稳定。

字段：
- `id` `bigint` PK
- `job_id` `bigint` FK -> `analysis_jobs.id`
- `word` `varchar(100)` NOT NULL
- `normalized_word` `varchar(100)` NOT NULL
- `source_type` `varchar(20)` NOT NULL
- `created_at` `timestamp` NOT NULL

说明：
- 该表是“任务级已掌握词快照”的一部分
- `source_type` 用于区分来源：`coca_level` 或 `user_vocabulary`

约束：
- 唯一索引：`(job_id, normalized_word, source_type)`
- 索引：`(job_id, normalized_word)`

### 3.7 `analysis_results`
用途：保存一次分析完成后的统计结果与导出文件信息。

字段：
- `id` `bigint` PK
- `job_id` `bigint` FK -> `analysis_jobs.id` UNIQUE
- `user_id` `bigint` FK -> `users.id`
- `book_id` `bigint` FK -> `books.id`
- `total_word_count` `int` NOT NULL
- `unique_word_count` `int` NOT NULL
- `to_memorize_word_count` `int` NOT NULL
- `coverage_95_word_count` `int` NOT NULL
- `reading_level` `varchar(20)` NOT NULL
- `reading_message` `varchar(255)` NOT NULL
- `all_words_file_key` `varchar(500)` NULL
- `to_memorize_file_key` `varchar(500)` NULL
- `coverage_95_file_key` `varchar(500)` NULL
- `created_at` `timestamp` NOT NULL
- `updated_at` `timestamp` NOT NULL

建议枚举：
- `reading_level`: `level_1`, `level_2`, `level_3`

规则：
- `level_1`: `coverage_95_word_count <= 200`
- `level_2`: `coverage_95_word_count BETWEEN 201 AND 799`
- `level_3`: `coverage_95_word_count >= 800`

约束：
- 唯一索引：`job_id`
- 索引：`(user_id, created_at DESC)`
- 索引：`(book_id, created_at DESC)`

### 3.8 `analysis_result_items`
用途：保存词级分析结果明细，支撑结果页与 CSV 导出。

字段：
- `id` `bigint` PK
- `result_id` `bigint` FK -> `analysis_results.id`
- `sequence_no` `int` NOT NULL
- `word` `varchar(100)` NOT NULL
- `lemma` `varchar(100)` NULL
- `book_frequency` `int` NOT NULL
- `coca_rank` `int` NULL
- `is_known` `boolean` NOT NULL
- `list_type` `varchar(30)` NOT NULL
- `created_at` `timestamp` NOT NULL

说明：
- `list_type` 表示该记录属于哪类导出列表
- 为减少重复，可允许同一词以不同 `list_type` 出现

建议枚举：
- `list_type`: `all_words`, `to_memorize`, `coverage_95`

约束：
- 索引：`(result_id, list_type, sequence_no)`
- 索引：`(result_id, word)`

## 4. 表关系

- 一个 `user` 可拥有多份 `user_vocabularies`
- 一份 `user_vocabulary` 可拥有多条 `user_vocabulary_items`
- 一本 `book` 可对应多个 `analysis_jobs`
- 一个 `analysis_job` 只对应一个 `analysis_result`
- 一个 `analysis_result` 可对应多条 `analysis_result_items`
- 一个 `analysis_job` 可对应多条 `analysis_job_vocabulary_snapshots`

## 5. 关键约束与业务规则

### 5.1 书籍去重
- 上传书籍后先计算 `file_hash`
- 若 `books.file_hash` 已存在，则不重复保存新书文件
- 用户仍可基于已有 `book_id` 创建新的 `analysis_job`

### 5.2 词表去重
- 用户上传 `TXT`，支持 `tab` 分隔导出格式或一行一个单词
- 导入时按 `normalized_word` 自动去重
- 重复词忽略，不报错

### 5.3 快照隔离
- 发起分析时，必须记录任务使用的已掌握词快照
- 用户后续修改词库，不得影响历史 `analysis_results`

### 5.4 删除策略
- 删除历史分析记录时，应删除：
  - `analysis_result_items`
  - `analysis_results`
  - `analysis_job_vocabulary_snapshots`
  - `analysis_jobs`
  - 对应导出文件
- 当某本书不再被任何分析任务引用时，才允许删除 `books` 记录及原始文件

## 6. 推荐索引

- `users(email)`
- `user_vocabularies(user_id, is_primary)`
- `user_vocabulary_items(user_id, normalized_word)`
- `books(file_hash)`
- `analysis_jobs(user_id, created_at DESC)`
- `analysis_jobs(book_id, created_at DESC)`
- `analysis_jobs(status, created_at)`
- `analysis_results(user_id, created_at DESC)`
- `analysis_result_items(result_id, list_type, sequence_no)`

## 7. 建议枚举定义

- 用户状态：`active`, `disabled`
- 词表来源：`manual`, `txt_upload`
- 书籍文本状态：`pending`, `ready`, `failed`
- 任务状态：`pending`, `processing`, `completed`, `failed`, `canceled`
- 任务错误码：`unsupported_format`, `parse_failed`
- 阅读等级：`level_1`, `level_2`, `level_3`
- 结果列表类型：`all_words`, `to_memorize`, `coverage_95`

## 8. 可选扩展

以下内容不属于当前 MVP 必需字段，但数据库设计应预留扩展空间：
- 用户阅读记录
- 词表标签与分组
- 分析版本号
- 词频算法版本
- 第三方词典或释义数据
- 任务重试次数与执行节点日志

## 9. 实施建议

第一阶段实现时，优先落地以下表：
- `users`
- `user_vocabularies`
- `user_vocabulary_items`
- `books`
- `analysis_jobs`
- `analysis_job_vocabulary_snapshots`
- `analysis_results`
- `analysis_result_items`

如果需要进一步降低实现复杂度，可先不做复杂审计字段和额外日志表，但不要省略快照表与结果明细表，否则后续会影响重复分析、历史一致性和导出能力。
