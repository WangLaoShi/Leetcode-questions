# 清洗与统一格式规则

`schema_version` 为 `1.0`。校验规则见 `problem.schema.json`，运行时由 `scripts/qb/schema_check.py` 执行。

## 身份

- `platform_question_id` 是平台内部 ID（neenza 的 `problem_id`，leetcode-api 的 `questionId`）。
- `display_id` 是展示题号（`frontend_id` / `questionFrontendId`，或 doocs 标题中的编号），保留原始字符串，不补零。
- 两者都用字符串。空字符串不当作标识，写成 `null`。
- doocs 没有内部 ID，`platform_question_id` 为 `null`。
- 链接主机名为 `leetcode.com` 时站点为 `leetcode.com`；为 `leetcode.cn` 时站点为 `leetcode.cn`。中文站不自动并入国际站。

## 枚举

- 类别：`algorithm`、`database`、`shell`、`concurrency`、`javascript`、`pandas`。来源原值留在 `raw.category`。来源没有类别时用 `null`，不用 `algorithm` 填空。
- 难度：`easy`、`medium`、`hard`。`简单/中等/困难` 与 `Easy/Medium/Hard` 映射到这三项。无法识别时为 `null`，原值留在 `raw.difficulty`。
- `is_paid_only` 只有来源明确给出布尔值才填写。未知为 `null`，不用 `false` 代替未知。

## 语言

- 题干语言只用 `en` 与 `zh-CN`。
- 编程语言写在 `starter_codes[].language`（如 `python3`、`mysql`），与题干语言分开。

## 空与未提取

每个内容字段有 `field_status`：

| 状态 | 含义 |
| --- | --- |
| `extracted` | 已提取出内容 |
| `confirmed_empty` | 来源有该字段且确认是空的 |
| `not_extracted` | 来源没提供，或正文里看见了标题但没拆开 |
| `not_applicable` | 该题型不使用这个扩展 |

空数组必须配上上述状态，不能单独表示“没有”或“还没看”。

## 题干

- 完整题干写入 `statement_markdown`。拆示例、约束失败时仍保留正文。
- HTML 转为 Markdown。代码块、表格、图片、上下标保留。
- neenza 的 `description` 经常只有 “Example 1:” 而没有输入输出。此时用其 `examples` 字段补进题干末尾，并保留结构化示例。
- 不把不同来源的段落拼成一篇题干。每个来源各自一条内容。

## 不导入的内容

- neenza 的 `solution` / `solutions`。
- leetcode-api 的 `solution` 对象（题解，不是函数签名）。
- doocs 中 `<!-- description:end -->` 之后的解法。没有 `description:start/end` 标记的 README 不导入，记入失败报告。
- 描述区内若出现解法标记，整篇拒绝导入。
- 初始代码只来自 `code_snippets` / `codeSnippets`。doocs 不读取 Solution 文件，模板状态为 `not_extracted`。

## 提示与约束

- 只保存来源里的题目提示字段。不从题解截取提示。
- 中文题干里的“提示”是约束标题，进入 `constraints`，不进入 `hints`。
- doocs 没有官方提示字段，`hints` 状态为 `not_extracted`。

## 题型扩展

SQL 题把含表头分隔线或 “Column Name / 列名” 的围栏代码放进 `type_specific.sql.schemas_and_samples`。pandas、shell、concurrency、javascript 只标记类型容器，不另造结构。这些内容同时留在题干里。

## 资源

图片只记录原始 URL、alt 和媒体类型。本阶段不下载二进制，`storage_path` 为空。

## 时间、编码、换行

- 时间是 UTC，格式 `YYYY-MM-DDThh:mm:ssZ`。
- 文件与 JSON 使用 UTF-8。
- 题干换行统一为 LF，不间断空格改为普通空格。

## 来源

每条记录的 `sources` 至少有一项，包含来源名、仓库、commit、路径、定位符、获取时间和文件 sha256。一条内容可以对应多个来源；当前标准化阶段一条记录先挂一个来源，导入时合并到同一题目上。
