---
name: amz
description: >
  amz-cli 是以 Product、Keyword 和 Market Entity 为业务主体的 Amazon 数据 SDK 统一入口，
  同时提供底层取数、确定性计算、原子推理和固定 SOP。
  本 skill 自带全量能力索引（references/capabilities.md，含每个能力的用途、必填参数、
  依赖链）和垂类 Agent 路由。Amazon 任务优先从 Entity 进入；只有没有对应 Entity 字段、
  已持有完整输入或需要调试底层能力时，才直接调用 Data、Calc 或 Analysis。

  当任务涉及 Amazon 商品/关键词/市场数据、利润率与 FBA 费用计算、VOC 评论分析、
  Listing 优化、竞品与市场分析、选品评估、新品/需求/风险判断，或需要调用
  amz-cli 的任意能力时使用——即使任务只提了「查一个 ASIN」「分析一个关键词」
  这类单点诉求，也先用本 skill 确认该走哪个能力。
---

# amz — Amazon 数据 SDK 调用技能

所有能力返回统一 Result JSON：`{code, message, data, meta}`，
`meta` 含 `upstream`（数据源）、`from_cache`、`enriched`（本次回填的实体字段）等溯源信息。

## 安装检查（每个新环境只做一次）

先运行 `amz version --json`。如果命令不存在，并且本 Skill 目录包含安装器与
`wheels/`，按当前系统运行：

```bash
# macOS / Linux
bash <本Skill目录>/install.sh

# Windows PowerShell
powershell -ExecutionPolicy Bypass -File <本Skill目录>\install.ps1

amz version --json
amz doctor
```

包装脚本会准备 `uv` 和独立 Python 3.12，再从网络下载当前系统所需的第三方依赖。
用户电脑不需要预装 Python。不要从源码仓库创建软链。

## 0. 定位能力（每任务先做这步）

```bash
# 先查本地能力索引——全部能力都在这一个文件里，按层分组，
# 每个能力一行：ID + 用途 + 必填参数 + 依赖链。
read references/capabilities.md
```

索引按 Agent 的推荐路由排列。先确定入口，再查具体能力：

- **Entity（默认）**：已知 Product、Keyword 或 Market，希望读取或生成它的字段。
- **Composite**：步骤、顺序和分支已经固定，希望复用完整流程。
- **Data**：没有对应 Entity 入口，或需要调试原始取数。包括 `product.*`、`keyword.*`、
  `market.*`、`category.*`、`ads.*` 和 `supply.*`。
- **Calc / Analysis**：已经持有完整输入，或 Entity 没有对应字段。Calc 做确定性计算，
  Analysis 做单一语义推理。

索引里没有的细节才需要动态查：

```bash
amz capabilities --id <capability_id>    # 单个能力完整 schema（可选参数/默认值/字段说明）
```

## 1. 调用方式：单能力走 CLI，多能力写 Python

### 单能力 → CLI

```bash
amz run <capability_id> --param key=value [--param k2=v2 ...] [--out FILE] [--task run_id]
```

- 值先按 JSON 解析（嵌套 dict/list 传 JSON 字符串，如 `'product_info={"title":"x"}'`），失败按字符串
- 调用前按 input_schema 强转类型：`"1"→1`、`"true"→True`
- 缺参/类型错返回 `ERROR_PARAM`，message 明确列出缺失字段与允许的键——据此修正重试

### 多能力串联 / 批量 / 循环 → 一个 Python 脚本

两次及以上能力调用需要在内存中传递结果、循环或批量时，写一个 Python 脚本一次跑完。
这样只启动一次解释器，也不需要在 shell 中转义嵌套 JSON。

```python
# /tmp/amz_task.py —— 执行：amz python /tmp/amz_task.py
import json
from amz import registry
from amz.envelope import Code

def call(cid: str, **params):
    r = registry.invoke(cid, params)
    if r.code != Code.OK:
        raise RuntimeError(f"{cid}: {r.code.value}: {r.message}")
    return r.data

# 例：从 Product 进入详情、利润和 VOC；Entity 自动补齐依赖并回填字段
asin = "B0GYFRH1L9"
detail = call("entity.product.product_details", asin=asin)
finance = call("entity.product.finance", asin=asin, shipping_method="fast")
voc = call("entity.product.voc", asin=asin)

# 例：批量（循环内自然复用结果）
for asin in ["B0GYFRH1L9", "B0FY6YWSVS"]:
    d = call("entity.product.finance", asin=asin, shipping_method="fast")
    print(asin, json.dumps(d, ensure_ascii=False))

# 例：Product → 主力词 → Keyword 趋势
keywords = call("entity.product.primary_keywords", asin="B0GYFRH1L9")
if keywords:
    top_term = keywords[0]["term"]
    trends = call("entity.keyword.trends", term=top_term, marketplace="US")
    print(json.dumps(trends, ensure_ascii=False, indent=2))
```

`amz python` 使用 CLI 自带的隔离环境，脚本可放在任意目录。它不会自动创建任务工作区；
需要调用时间线和中间文件时，使用第 3 节的 `amz task`，或在脚本中显式建立 Runtime 上下文。

## 2. 实体能力优先

`entity.*` 走实体 lazy 链路：自动 fetch 依赖字段、级联 enrich、TTL 回填，
一次调用拿到完整结果，不用手工拼多个能力。索引里 `requires` 标注了
自动级联内容——能走 `entity.*` 就不裸调 `calc.*`/`analysis.*`。

核心 Entity 只有 `Product`、`Keyword` 和 `Market`。Review 和 Finance 是 Product 的字段模型，
不是独立业务 Entity。Entity 关系只保存 `EntityRef`，调用方不应自行拼接或展开缓存文件。

```bash
amz run entity.product.finance    --param asin=B0GYFRH1L9 shipping_method=fast
amz run entity.product.weaknesses --param asin=B0GYFRH1L9   # 自动补 reviews + product_details
amz run entity.product.reviews    --param asin=B0GYFRH1L9 mode=mid
amz run entity.product.market_stats --param asin=B0GYFRH1L9
amz run entity.product.market_profile --param asin=B0GYFRH1L9
amz run entity.product.market_opportunity --param asin=B0GYFRH1L9
amz run entity.keyword.trends     --param term="portable blender" marketplace=US category=
amz run entity.keyword.market_stats --param term="portable blender" marketplace=US category=
amz run entity.keyword.market_profile --param term="portable blender" marketplace=US category=
amz run entity.keyword.market_opportunity --param term="portable blender" marketplace=US category=
```

Product 与 Keyword 的 Market 门面能力都是正式的 `entity.*` 能力：调用
profile/opportunity 时会自动级联建立 Market 并补齐 Stats。Skill 不需要自己编排
`entity.market.*`。

身份字段（`asin`/`term` 等）必填；getter 参数（如 `shipping_method`）可选。

`requires` 是声明式依赖，不表示 Registry 会自动执行前置能力。必须裸调 `calc.*` 或
`analysis.*` 时，先按其 input schema 准备完整输入；需要任务记录时，把相关调用挂到同一个
`run_id`。收到 `ERROR_MISSING_FIELDS` 时读取 `meta.missing`，优先改走能自动补字段的 Entity。

## 3. 任务与中间文件

多步 CLI 任务用 `amz task run`，自动建任务工作区并记录每次调用的结果文件与实体缓存：

```bash
amz task run <capability_id> --param ...                  # 自动建任务 → 返回 run_id + result_file
amz task run <capability_id> --param ... --task <run_id>  # 挂到已有任务
amz task status <run_id>            # 状态 + 调用时间线 + 文件清单
amz task files <run_id> --kind entity   # 实体缓存文件路径（直接读 JSON）
amz task cleanup --older-than-hours 168 # 清理过期任务工作区
```

## 4. 常见场景（可直接复制）

```bash
# 商品详情（慢端点，首调 10-30s）
amz run entity.product.product_details --param asin=B0GYFRH1L9

# 利润率 / FBA / 资金效率
amz run entity.product.finance --param asin=B0GYFRH1L9 shipping_method=fast

# VOC：优势、弱点和使用洞察（自动级联评论与详情）
amz run entity.product.voc --param asin=B0GYFRH1L9

# Product 的主力词；Keyword 的特征和趋势
amz run entity.product.primary_keywords --param asin=B0GYFRH1L9
amz run entity.keyword.metrics --param term="portable blender" marketplace=US category=
amz run entity.keyword.trends --param term="portable blender" marketplace=US category=

# Market 竞品、画像和机会
amz run entity.keyword.products --param term="portable blender" marketplace=US category=
amz run entity.keyword.market_profile --param term="portable blender" marketplace=US category=
amz run entity.keyword.market_opportunity --param term="portable blender" marketplace=US category=

# 确定性计算（无需网络）
amz run calc.listing.word-diff --param old_text="a b c" new_text="a x c"
```

其余 60+ 能力（COSMO、需求评估、创新评估、市场缺口、进入时机、材质门槛、
类目树、Rufus、1688 供应商、SIF 广告漏斗等）都在 `references/capabilities.md`，
接任务时按关键词查索引，别凭印象选能力。

## 5. 垂类 Agent 路由

下列任务需要根据中间证据动态选择、循环或停止时，使用对应 Skill。Skill 是独立入口，
不会注册成 `amz capabilities` 中的 Python 能力。
在 V1 发布包中，按名称读取 `skills/<name>/SKILL.md`。

| 用户目标 | Skill | 关键 CLI 入口 |
|---|---|---|
| 安装 CLI、初始化或配置 API Key / Token | `amz-setup` | `amz setup --web`、`amz setup --status --json` |
| 验证未上架新品想法 | `amz-concept-check` | `entity.keyword.*`、`entity.product.voc` |
| 理解市场驱动、方案变化和用户场景 | `amz-market-insight` | `entity.keyword.market_*`、`entity.product.voc` |
| 判断现在入局是否错过需求窗口 | `amz-market-timing` | `entity.product.product_details`、`entity.keyword.trends`、`analysis.market.timing` |
| 从一批竞品生成产品改进提案 | `amz-product-improve` | `entity.product.voc`、`analysis.market.*` |
| 检查法规、类目和 FBA 准入 | `amz-risk-entry` | `entity.product.product_details` + 当前官方来源 |
| 快筛专利、商标、版权和授权 IP | `amz-risk-ip` | `entity.product.innovation` + 官方 IP 数据库 |
| 深查专利候选、状态和相关性 | `patent-analysis` | Product Entity + USPTO/专利数据库 |

`amz-product-improve` 以 Product Entity 的 `strengths`、`weaknesses` 和
`use_insights` 为唯一正式产品洞察入口。不要回退到旧 `amz-api` 脚本或
`product_dev_v2` 私有管线。

## 6. 错误码处理

| code | 含义 | 处理 |
|---|---|---|
| `ERROR_PARAM` | 参数缺失/类型错误 | 按 message 列出的字段修正后重试 |
| `ERROR_AUTH` | token 缺失/无效 | `amz setup` 或设 `AMZ_API_TOKEN` |
| `ERROR_UPSTREAM` | 上游失败/实体 fetch 失败 | 看 `meta.hint`；重试或降级（如 market.snapshot 自动降级） |
| `ERROR_RATE_LIMIT` | 限流 | 退避后重试 |
| `ERROR_LLM` | LLM 调用失败 | 重试或换模型（`analysis.*` 需要 DEEPSEEK_API_KEY） |
| `ERROR_MISSING_FIELDS` | Calc/Analysis 输入字段不完整 | 读 `meta.missing`；优先改走 Entity 补字段 |
| `ERROR_CACHE_MISS` | 指定缓存未命中 | 允许取数时改走 Entity ensure；只读场景直接报告缺失 |
| `ERROR_NOT_FOUND` | 能力不存在/资源缺失 | 检查能力 ID |
| `ERROR_SERVER_INTERNAL` | SDK 未预期异常 | 保留 capability 和 message，停止盲目重试 |

## 7. 注意点

- **慢端点**：`product.get`、`entity.product.product_details` 首调 10-30s，bash 超时给足 60s+
- **API Key 配置**：交给 `amz-setup` Skill 打开本机安全页面。不要要求普通用户输入命令，
  也不要让用户把密钥发到聊天中。发布包不包含任何 API Key
- **缓存**：`~/.cache/amz-cli/`（实体缓存 + 任务工作区）；`amz task cleanup` 定期清理
- **环境自检**：报错先跑 `amz doctor`；命令不存在时按“安装检查”执行 Skill 自带安装器
- **索引版本**：以当前 Skill 的 `references/capabilities.md` 为快速索引；完整 schema
  始终以已安装 CLI 的 `amz capabilities --id <id>` 为准

## 参考

- `references/capabilities.md` — 能力全索引（自动生成）
- `skills/<name>/SKILL.md` — 垂类 Agent 的动态编排说明
- `README.md` — CLI-first 接入细节
