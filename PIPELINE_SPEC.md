# PIPELINE SPEC

## 1. 目标

本文件定义英文书籍词汇分析系统的后端内部流水线。目标不是保留现有脚本式执行方式，而是将现有 `extract_words.py`、`merge_word_freq.py`、`coverage_analysis.py` 抽象为可在 `FastAPI` + 异步任务系统中运行的稳定分析流程。

流水线必须支持：
- `epub` 解析
- 英文文本抽取
- 单词提取与词频统计
- 原型解析与 `COCA` 排名匹配
- 已掌握词过滤
- 95% 覆盖计算
- 三类 CSV 生成
- 阅读等级判定

## 2. 设计原则

- 对外暴露单次分析任务接口，对内拆分阶段执行
- 每个阶段输入输出清晰，可单独测试
- 核心中间结果应可落库或缓存，便于重试与排障
- 历史结果必须依赖任务快照，不能依赖用户当前实时词库
- 文件生成与数据库写入分离，避免单点失败污染任务状态

## 3. 流水线阶段总览

一次分析任务建议拆为以下阶段：

1. `validate_input`
2. `load_book_file`
3. `extract_book_text`
4. `detect_language`
5. `extract_word_tokens`
6. `build_word_frequencies`
7. `resolve_lemma_and_coca_rank`
8. `build_known_words_snapshot`
9. `mark_known_words`
10. `build_output_lists`
11. `calculate_coverage_95`
12. `calculate_reading_level`
13. `generate_csv_files`
14. `persist_result_snapshot`
15. `finalize_job`

## 4. 阶段定义

### 4.1 `validate_input`
职责：
- 校验 `book_id` 是否存在
- 校验 `known_words_level` 是否在 `1000..15000`
- 校验任务创建用户是否有权限访问该书

输入：
- `user_id`
- `book_id`
- `known_words_level`

输出：
- 合法任务上下文

失败：
- 非法参数
- 书籍不存在
- 权限不足

### 4.2 `load_book_file`
职责：
- 从对象存储或服务器文件存储中加载原始 `epub`

输入：
- `book.storage_key`

输出：
- 文件流或临时本地文件路径

失败：
- 文件不存在
- 存储服务不可用

### 4.3 `extract_book_text`
职责：
- 遍历 `epub` 中的 HTML/XHTML 资源
- 移除 HTML 标签、脚本和样式
- 拼接成完整纯文本

实现来源：
- 现有 `extract_words.py` 中的 `extract_text_from_epub` 与 `remove_html_tags`

输入：
- `epub` 文件

输出：
- `raw_text`

失败：
- `epub` 解析失败

### 4.4 `detect_language`
职责：
- 对抽样文本做英文检测
- 若非英文占比过高，则拒绝分析

输入：
- `raw_text`

输出：
- `language = en`
- 或错误状态

说明：
- MVP 可采用宽松规则，只做基础文本抽样检测

### 4.5 `extract_word_tokens`
职责：
- 从文本中提取英文单词
- 统一转小写
- 过滤无效单字母，仅保留合法单字母如 `a`, `i`, `o`

实现来源：
- 现有 `extract_words.py` 中的 `extract_words`

输入：
- `raw_text`

输出：
- `tokens: list[str]`

### 4.6 `build_word_frequencies`
职责：
- 统计全书总词数
- 统计唯一词频，并按频率降序排列

实现来源：
- 现有 `extract_words.py` 中的 `count_word_frequencies`

输入：
- `tokens`

输出：
- `total_word_count`
- `unique_word_count`
- `word_frequency_items`

`word_frequency_items` 结构建议：

```json
[
  {
    "word": "example",
    "book_frequency": 42
  }
]
```

### 4.7 `resolve_lemma_and_coca_rank`
职责：
- 基于 `ecdict` 解析单词原型
- 优先用原词匹配 `COCA` 排名
- 若原词未命中，再用原型匹配 `COCA` 排名

实现来源：
- 现有 `merge_word_freq.py`

关键规则：
- `ecdict.exchange` 中 `0:` 表示原型
- `COCA` 排名词表若重复，保留首次出现项，即最小排名
- 需保留不规则动词回退映射，如 `was -> be`

输入：
- `word_frequency_items`
- `ecdict`
- `coca_rank_dictionary`

输出：

```json
[
  {
    "word": "went",
    "lemma": "go",
    "book_frequency": 8,
    "coca_rank": 123,
    "rank_match_type": "lemma"
  }
]
```

### 4.8 `build_known_words_snapshot`
职责：
- 根据 `known_words_level` 提取对应 `COCA` 范围词
- 读取当前用户主词库词条
- 合并为并集
- 为本次任务保存已掌握词快照

输入：
- `known_words_level`
- `user_vocabulary_items`
- `coca_rank_dictionary`

输出：
- `known_words_set`
- `analysis_job_vocabulary_snapshots`

关键规则：
- 当前规则为“`COCA 1000..15000` 下拉选择 + 用户词库并集”
- 快照必须任务级保存，不能引用实时词库

### 4.9 `mark_known_words`
职责：
- 为每个词标记 `is_known`

输入：
- `resolved_word_items`
- `known_words_set`

输出：

```json
[
  {
    "word": "example",
    "lemma": "example",
    "book_frequency": 42,
    "coca_rank": 999,
    "is_known": false
  }
]
```

规则：
- 可优先按 `word` 匹配
- 如有需要，允许后续扩展为按 `lemma` 辅助匹配

### 4.10 `build_output_lists`
职责：
- 构建三类导出列表：
  - `all_words`
  - `to_memorize`
  - `coverage_95`

定义：
- `all_words`：全量唯一词
- `to_memorize`：过滤 `is_known = true` 后剩余词
- `coverage_95`：基于当前已掌握覆盖率，在 `to_memorize` 中按词频补齐后让全书累计覆盖率达到 95% 所需的最小增量词集合

输出记录统一字段：
- `sequence_no`
- `word`
- `lemma`
- `book_frequency`
- `coca_rank`
- `is_known`

### 4.11 `calculate_coverage_95`
职责：
- 以全书总词频为分母
- 先计算已掌握词对全书的当前覆盖率
- 若当前覆盖率已达到 `95%`，直接返回空集合
- 若未达到 `95%`，再对待记忆词按 `book_frequency` 降序累计补齐
- 找出让全书累计覆盖率达到 `95%` 所需的最小未知词集合

实现来源：
- 现有 `coverage_analysis.py`

输入：
- `all_word_items`
- `to_memorize_items`
- `total_word_count`

输出：
- `coverage_95_word_count`
- `coverage_95_items`

注意：
- 当前产品定义不是“覆盖待记忆词总频次的 95%”
- 也不是“仅靠未知词自身累计到全书 95%”
- 而是“已掌握词频 + 新学习词频”共同达到全书总词频的 `95%`

### 4.12 `calculate_reading_level`
职责：
- 基于 `coverage_95_word_count` 计算阅读建议等级

规则：
- `level_1`: `<= 200`
- `level_2`: `201-799`
- `level_3`: `>= 800`

输出：

```json
{
  "reading_level": "level_2",
  "reading_label": "推荐阅读 + 学习",
  "reading_color": "yellow",
  "reading_message": "可以阅读，但建议先学习核心词表。"
}
```

### 4.13 `generate_csv_files`
职责：
- 为三类结果分别生成 CSV 文件
- 上传到对象存储或服务器文件存储
- 返回文件标识

输出文件：
- `all_words.csv`
- `to_memorize.csv`
- `coverage_95.csv`

字段顺序必须固定：
- `序号`
- `单词`
- `书籍出现频率`
- `COCA 排行`
- `原型`
- `是否已掌握`

### 4.14 `persist_result_snapshot`
职责：
- 写入 `analysis_results`
- 写入 `analysis_result_items`
- 保存汇总统计、阅读等级和文件地址

关键要求：
- 数据库写入应尽量在事务中完成
- 文件已生成但数据库写入失败时，需有补偿策略或清理策略

### 4.15 `finalize_job`
职责：
- 更新任务状态
- 成功时写入 `completed`
- 失败时写入 `failed` 和错误码

可用错误码：
- `unsupported_format`
- `parse_failed`
- `internal_error`

## 5. 推荐模块拆分

建议后端内部按如下模块实现：

- `services/book_loader.py`
- `services/text_extractor.py`
- `services/language_detector.py`
- `services/tokenizer.py`
- `services/frequency_counter.py`
- `services/lemma_resolver.py`
- `services/coca_rank_matcher.py`
- `services/known_words_builder.py`
- `services/coverage_calculator.py`
- `services/reading_level.py`
- `services/csv_exporter.py`
- `services/analysis_pipeline.py`

其中：
- `analysis_pipeline.py` 负责串联各阶段
- 其他模块负责单一职责逻辑

## 6. 中间数据模型建议

建议在服务内部统一使用以下几个核心 DTO：

### 6.1 `WordFrequencyItem`

```json
{
  "word": "example",
  "book_frequency": 42
}
```

### 6.2 `ResolvedWordItem`

```json
{
  "word": "went",
  "lemma": "go",
  "book_frequency": 8,
  "coca_rank": 123,
  "rank_match_type": "lemma",
  "is_known": false
}
```

### 6.3 `AnalysisSummary`

```json
{
  "total_word_count": 78579,
  "unique_word_count": 5766,
  "to_memorize_word_count": 836,
  "coverage_95_word_count": 214,
  "reading_level": "level_2"
}
```

## 7. 任务执行与重试建议

- `validate_input` 失败直接终止，不重试
- `extract_book_text` 若因解析失败报错，标记 `parse_failed`
- 文件存储短暂异常可有限次重试
- 数据库写入失败应支持任务失败回滚或补偿清理
- 不应对逻辑错误做无限重试

## 8. 可测试点

每个阶段都应至少有独立测试或样例验证：

- `extract_book_text`：能正确抽出 XHTML 正文
- `extract_word_tokens`：能过滤无效单字符
- `build_word_frequencies`：频次排序正确
- `resolve_lemma_and_coca_rank`：原词优先，原型回退正确
- `build_known_words_snapshot`：并集逻辑正确
- `calculate_coverage_95`：按全书总词频计算正确
- `calculate_reading_level`：边界值 `200 / 201 / 799 / 800` 正确
- `generate_csv_files`：字段顺序与列名固定

## 9. 与现有脚本的映射

- `extract_words.py`
  - 对应：`extract_book_text`、`extract_word_tokens`、`build_word_frequencies`
- `merge_word_freq.py`
  - 对应：`resolve_lemma_and_coca_rank`
- `coverage_analysis.py`
  - 对应：`calculate_coverage_95`

现有脚本可继续作为算法参考，但不应直接作为生产后端入口。后续应将其逻辑迁移为可复用服务模块。
