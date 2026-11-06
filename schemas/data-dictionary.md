# 字段字典与关系

运行库是 SQLite（`migrations/sqlite/001_init.sql`）。PostgreSQL 脚本在 `migrations/postgres/001_init.sql`，类型对应关系：SQLite `TEXT` JSON 对应 PostgreSQL `JSONB`，`INTEGER` 0/1 对应布尔，时间文本对应 `TIMESTAMPTZ`。

内部主键都是自增整数，不使用 LeetCode 展示题号。

## 表

| 表 | 作用 | 删除规则 |
| --- | --- | --- |
| `problem` | 题目生命周期、规范类别、难度、会员标志 | 子表 `ON DELETE RESTRICT`。导入程序不删除题目 |
| `problem_source_identity` | 平台、站点、内部 ID、展示题号、slug、链接 | 标识列禁止空字符串。三个局部唯一索引只约束非空值 |
| `problem_content` | 某站点身份下一种语言的一个正文版本 | 挂 `source_identity_id`。`is_current` 每种语言一条 |
| `content_revision` | 指向当前版本和上一版本，并记录原因 | 不删除历史正文 |
| `problem_example` | 属于某个正文版本的示例 | 唯一 `(content_id, ordinal)` |
| `problem_hint` | 属于某个正文版本的提示 | 唯一 `(content_id, locale, ordinal)` |
| `tag` / `problem_tag` | 标签多对多 | 关联主键防止重复 |
| `starter_code` | 某语言模板及是否疑似完整实现 | 唯一 `(problem_id, language, content_hash)` |
| `asset` / `content_asset` | 图片 URL 与正文的关系 | 二进制不入库。URL 唯一 |
| `source_record` | 仓库路径、commit、获取时间、文件哈希 | 唯一 `(来源, 路径, commit, 哈希)` |
| `content_provenance` | 内容对象指向来源记录和提取位置 | 唯一 `(对象类型, 对象, 来源, 定位符)` |
| `import_batch` | 批次状态、数量、起止时间 | `dry_run` 批次会随事务回滚 |
| `data_issue` | 缺失、冲突、隔离、疑似实现 | `fingerprint` 唯一，状态默认 `open` |

## 版本与事务

- 正文更新新增一行，修订号加一，旧行保留，示例仍指向旧 `content_id`。
- 一批导入是一个事务；每题一个 savepoint。失败的题回滚，不留下半条身份或半条正文。
- 来源文件后来消失不会触发删除。

## 索引

展示题号、slug、内部 ID、类别、难度、题目标签、正文标题、当前语言版本、模板语言均有索引，供按题号、slug、标题、类别、难度和标签查询。

## 不适用与未知

- `problem.is_paid_only` 为 SQL `NULL` 表示未知。
- `problem.category` / `difficulty` 为 `NULL` 表示未知或来源未提供。
- 内容是否提取看 `field_status_json`，不靠空数组猜测。
