# 来源字段映射

数量以 `reports/source-inventory.json` 为准。下表是字段怎么进统一格式。仓库许可证不自动覆盖题干，说明见 `manifests/snapshot.json`。

## neenza/leetcode-problems

单题文件 `problems/*.json`。`merged_problems.json` 是同一批数据的合并副本，不导入。

| 来源字段 | 类型 | 统一字段 | 说明 |
| --- | --- | --- | --- |
| `problem_id` | string | `identity.platform_question_id` | 内部 ID，常与展示题号不同 |
| `frontend_id` | string | `identity.display_id` | 展示题号 |
| `problem_slug` | string | `identity.slug` | 站点固定为 leetcode.com |
| `title` | string | `contents[].title` | 英文标题 |
| `difficulty` | string | `difficulty` + `raw.difficulty` | Easy/Medium/Hard |
| `description` | string | `statement_markdown` | 多为 Markdown/纯文本，有时含 HTML |
| `examples[]` | array | `examples` | `example_text` 拆成输入、输出、解释；`images` 为 URL |
| `constraints` | array | `constraints` | 独立字段；正文里再出现则保留正文 |
| `follow_ups` | array | `follow_ups` | 空数组表示确认没有 |
| `hints` | array | `hints` | 题目提示 |
| `topics` | array of string | `tags` | 词表 `leetcode-topic` |
| `code_snippets` | object | `starter_codes` | 键是语言，值是模板 |
| `solution` / `solutions` | string | 不导入 | 题解。只记“已排除” |
| 类别、是否会员 | 无 | `null` | 未知，不猜测 |

没有类别字段。没有非数字展示题号。

## noworneverev/leetcode-api

主文件 `data/leetcode_questions.json`，元素形状为 `{data: {question: ...}}`。这是 GraphQL `questionData` 缓存，不是详情接口的另一种文档。公开抽样 `GET /problem/two-sum` 返回去掉外层包装后的同一题目对象，并且仍带 `solution`。

| 来源字段 | 类型 | 统一字段 | 说明 |
| --- | --- | --- | --- |
| `questionId` | string | `platform_question_id` | 内部 ID |
| `questionFrontendId` | string | `display_id` | 本快照中全部为数字字符串，且无重复 |
| `url` | string | `slug` 与 `url` | 缓存里通常没有 `titleSlug`，从 URL 解析 |
| `title` | string | `title` | |
| `categoryTitle` | string | `category` | Algorithms/Database/Shell/Concurrency/JavaScript/pandas |
| `difficulty` | string | `difficulty` | |
| `isPaidOnly` | bool | `is_paid_only` | 本缓存中付费题的 `content` 为空 |
| `content` | string 或空 | `statement_markdown` | HTML。示例和约束嵌在正文里 |
| `hints` | array | `hints` | 独立字段 |
| `topicTags[].name` | array | `tags` | 词表 `leetcode-topic` |
| `codeSnippets[]` | array | `starter_codes` | `langSlug` + `code`，这是模板不是答案 |
| `solution` | object | 不导入 | `canSeeDetail` / `content` 属于题解 |
| `likes`、`stats`、`similarQuestions`、`companyTags` | 多种 | 不导入 | 不属于题目信息范围 |

`leetcode_questions_mini.json` 只有列表字段，不作为正文来源。

## doocs/leetcode

稀疏检出只保留 `solution/**/README.md` 与 `README_EN.md`。没有 Solution 源文件。

| 区域 | 统一字段 | 说明 |
| --- | --- | --- |
| 标题链接 `# [编号. 标题](url)` | `display_id`、`title`、`slug`、`url`、`site` | `.cn` 与 `.com` 分开 |
| front matter `difficulty` | `difficulty` | 含中文难度 |
| front matter `tags` | `tags` | 词表 `doocs`。仅当标签明确是数据库、Shell、pandas、并发、JavaScript 时填写类别 |
| `<!-- description:start -->` 到 `description:end` | `statement_markdown` | HTML。代码块保留 |
| 描述区之后的解法 | 不导入 | 包括“解法 / Solutions” |
| 官方提示、内部 ID、会员标志、初始模板 | `null` 或 `not_extracted` | 仓库未以独立字段提供 |

中文 README 语言为 `zh-CN`，英文 README 为 `en`。

## 尚未出现的范围

三个快照都没有非数字展示题号，也没有单独的 leetcode.cn 官方导出。面试题、LCP 等特殊编号记为来源缺口，不编造记录。
