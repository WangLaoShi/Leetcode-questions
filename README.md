# LeetCode 题目信息数据库

这是一个可以下载到本地直接查询的 LeetCode 题目信息库。数据在 SQLite 文件里，只用 Python 标准库就能查，不需要安装数据库服务器。

库里保存的是题目本身：题号、标题、难度、类别、题干、示例、约束、提示、初始代码模板、标签，以及每条内容来自哪个快照。不含题解、复杂度分析和答案实现。初始代码模板是 LeetCode 给出的空函数框架，不是解答。

## 下载

```bash
git clone https://github.com/yumengwang63-eng/Leetcode-questions.git
cd Leetcode-questions
```

克隆体积大约 90MB，主要来自 `db/question-bank.sqlite`。也可以在 GitHub 页面用 Code → Download ZIP。

需要 Python 3.10 或更高版本。不需要 pip 安装第三方包。本机不需要单独安装 `sqlite3` 命令。

## 库里有什么

构建时的统计：

| 项目 | 数量 |
| --- | --- |
| 题目 | 8202 |
| 其中 leetcode.com | 4101 |
| 其中 leetcode.cn | 4101 |
| 题干版本 | 15216 |
| 示例 | 33847 |
| 提示 | 10880 |
| 初始代码模板 | 61386 |

leetcode.com 上这份快照里的 4101 个 slug 都在库中。中文题来自 doocs 的中文 README，按 `leetcode.cn` 单独存放，没有自动并进国际站题目。对应关系在 `reports/cross-site-candidates.jsonl`，状态是待核实。

更细的分类、难度和字段缺失统计见 `reports/coverage.json` 与 `reports/quality.json`。

## 用命令查询

在仓库根目录执行。PowerShell 示例：

```powershell
$env:PYTHONPATH = "$pwd\scripts"
$env:PYTHONUTF8 = "1"

python -m qb.cli query --db db\question-bank.sqlite --slug two-sum --site leetcode.com --locale en
python -m qb.cli query --db db\question-bank.sqlite --display-id 1
python -m qb.cli query --db db\question-bank.sqlite --title 两数之和 --site leetcode.cn --locale zh-CN
python -m qb.cli query --db db\question-bank.sqlite --category database --difficulty easy --limit 10
python -m qb.cli query --db db\question-bank.sqlite --issues
```

macOS 或 Linux 把路径写成 `scripts` 和 `db/question-bank.sqlite` 即可。

这条命令返回题号、slug、标题、难度、类别、语言和题干长度，方便确认题目在不在。它不打印整篇题干。

可用筛选：

| 参数 | 含义 |
| --- | --- |
| `--slug` | 例如 `two-sum` |
| `--display-id` | 展示题号，例如 `1`。这不是平台内部 ID |
| `--title` | 标题，按包含关系匹配 |
| `--site` | `leetcode.com` 或 `leetcode.cn` |
| `--locale` | `en` 或 `zh-CN` |
| `--category` | `algorithm`、`database`、`shell`、`concurrency`、`javascript`、`pandas` |
| `--difficulty` | `easy`、`medium`、`hard` |
| `--limit` | 条数，默认 20 |
| `--issues` | 改看缺失、冲突和待核实问题的数量 |

## 查看完整题干、示例、提示和模板

`queries/examples.sql` 里有按题号、标签、正文、示例、提示、模板、来源和问题列表查询的语句。用 Python 执行其中一条即可，例如读英文 Two Sum 的题干开头：

```powershell
python -c "import sqlite3; c=sqlite3.connect(r'db/question-bank.sqlite'); print(c.execute(\"SELECT statement_markdown FROM problem_content ct JOIN problem_source_identity i ON i.id=ct.source_identity_id WHERE i.slug='two-sum' AND i.site='leetcode.com' AND ct.locale='en' AND ct.is_current=1\").fetchone()[0])"
```

查的时候加上 `is_current = 1`，得到的是当前选用的版本。历史版本仍留在 `problem_content` 里，`revision` 更大的不一定是当前版本，以 `is_current` 为准。

主要的表：

| 表 | 内容 |
| --- | --- |
| `problem` | 内部主键、类别、难度、是否会员 |
| `problem_source_identity` | 站点、内部 ID、展示题号、slug、链接 |
| `problem_content` | 某种语言的题干版本 |
| `problem_example` | 挂在某一版题干上的示例 |
| `problem_hint` | 挂在某一版题干上的提示 |
| `starter_code` | 各语言初始模板 |
| `tag`、`problem_tag` | 标签 |
| `source_record`、`content_provenance` | 来源文件、commit、提取位置 |
| `data_issue` | 缺失、冲突和待核实项 |

字段说明在 `schemas/data-dictionary.md`。建表语句在 `migrations/sqlite/001_init.sql`。同一套表的 PostgreSQL 写法在 `migrations/postgres/001_init.sql`，本库实际跑的是 SQLite。

## 数据从哪里来

三份公开快照，获取时间和 commit 记在 `manifests/snapshot.json`：

| 来源 | 用在这里的部分 |
| --- | --- |
| [neenza/leetcode-problems](https://github.com/neenza/leetcode-problems) | 英文题干、示例、约束、提示、初始模板 |
| [noworneverev/leetcode-api](https://github.com/noworneverev/leetcode-api) | leetcode.com 题目列表、HTML 题干、会员标志、模板 |
| [doocs/leetcode](https://github.com/doocs/leetcode) | 只取 README 里 `description:start` 到 `description:end` 之间的题干 |

这些仓库的许可证不自动覆盖 LeetCode 题目原文。neenza 仓库没有 LICENSE 文件。leetcode-api 仓库软件是 MIT。doocs 仓库是 CC BY-SA 4.0。题目文字的权利仍属于原权利人。本仓库只便于本地查阅从这些公开快照整理出的题目信息。

字段怎么对应，见 `schemas/source-field-mapping.md`。

## 使用时要注意

- 付费题在 leetcode-api 缓存里没有正文，这里没有再向 LeetCode 抓取会员内容。若 doocs 快照里已有题干，会作为 doocs 来源另存。
- 中文站和国际站没有合并。查英文用 `--site leetcode.com --locale en`，查中文用 `--site leetcode.cn --locale zh-CN`。
- 中文算法题如果没有可靠类别标签，`category` 为空。
- 这三份快照里没有 LCP、面试题这类非数字题号。
- 图片只保存原始 URL，没有把图片文件放进库里。
- 同一题不同来源的正文如果有差异，会各留一份，不会拼成一篇。当前展示哪一份由 `is_current` 决定。

## 这个仓库不包含什么

不包含三个来源仓库的原始克隆，也不包含重新抓取脚本所需的上游文件。因此克隆本仓库后可以直接查询，不能在本目录里把三份来源重新跑一遍导入。查询代码在 `scripts/qb/`。
