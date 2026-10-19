---
name: amz
description: >
  amz-cli 是以 Product、Keyword 和 Market Entity 为业务主体的 Amazon 数据 SDK 统一入口，
  同时提供底层取数、确定性计算、原子推理和固定 SOP。
  本 skill 自带全量能力索引（references/capabilities.md，含每个能力的用途、必填参数、
  依赖链）和垂类 Agent 路由。Amazon 任务优先从 Entity 进入；Calc 和 Analysis 由 Entity 方法内部调用；没有 ASIN 的新品使用 ProductDraft，不裸调 Calc 或 Analysis。

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

Entity 是计算和分析业务的唯一对外主体。Skill 选择 Entity 方法或已注册 Composite，由 Entity 准备依赖、检查有效证据并管理结果。Calc 和 Analysis 是内部实现，不允许直接执行；旧 Calc / Analysis ID 的迁移见 [调用映射](references/routes.md)。

本文的 `references/` 相对本 Skill 目录解析；命令中的脚本路径应先转成安装目录下的绝对路径，
不假设当前工作目录就是 Skill 目录。

```bash
# 先查本地能力索引——全部能力都在这一个文件里，按层分组，
# 每个能力一行：ID + 用途 + 必填参数 + 依赖链。
read references/capabilities.md
```

索引按 Agent 的推荐路由排列。先确定入口，再查具体能力：

- **Entity**：读取字段或执行改写、比较、提案等任务方法；无 ASIN 使用 ProductDraft。
- **Composite**：步骤、顺序和分支已经固定，希望复用完整流程。
- **Data**：保留供 SDK 调试；Skill 业务流程只使用 Entity / Composite。Calc 与 Analysis 不属于公开调用接口，已有完整数据也不能绕过 Entity。

索引里没有的细节才需要动态查：

```bash
amz capabilities --id <capability_id>    # 单个能力完整 schema（可选参数/默认值/字段说明）
```

## 1. 调用方式：单能力走 CLI，多能力写 Python

### 单能力 → CLI

```bash
amz run <capability_id> --param key=value [--param k2=v2 ...] [--out FILE] [--task run_id]
```

- 值先按 JSON 解析（嵌套 dict/list 传 JSON 字符串，如 `'keywords={"S":["water bottle"]}'`），失败按字符串
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
自动级联内容——业务分析必须走 `entity.*`，不裸调 `calc.*` 或 `analysis.*`。

Amazon 核心 Entity 为 `Product`、`Keyword` 和 `Market`；本地 `ProductDraft` 保存用户提供的新概念或文案事实。Review 和 Finance 是 Product 的字段模型，
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

Product 与 Keyword 的 profile/opportunity 门面仍用于市场数值画像和机会评分。
解决方案分类、人群/场景概述使用 `entity.market.summary`；跨商品 COSMO 特征覆盖使用
`entity.market.cosmo`。它们的输出不同，按问题选择，不用机会分冒充评论缺口或语义分析。
用户已给关键词时直接传 `term`；只有 ASIN 时通过 `entity.product.primary_keyword_ref` 返回的 Ref，
用 `EntityRef.model_validate(result.data).identity` 取得 Market 身份参数，详见调用映射示例。

身份字段（`asin`/`term`/`draft_id` 等）必填；其他必需任务参数以 schema 为准。

`requires` 仅描述依赖；自动补数据由 Entity 方法执行。带上下文的任务方法接收实体身份/Ref、样本范围和业务参数，不接受任意字典覆盖本品事实。收到缺字段或上游失败时报告原因并停止该分析，不编造占位数据，也不调用内部实现绕过。

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

# 利润率 / FBA / 资金效率（默认自动取最新日参考汇率，结果含日期与来源）
amz run entity.product.finance --param asin=B0GYFRH1L9 shipping_method=fast

# 显式汇率用于固定假设复算；最新汇率可用 data.fx.rate 单独查询
amz run entity.product.finance --param asin=B0GYFRH1L9 exchange_rate=7.0

# VOC：优势、弱点和使用洞察（自动级联评论与详情）
amz run entity.product.voc --param asin=B0GYFRH1L9

# 单品语义、材质及复制难度：按用户问题选择一项，自动准备输入和缓存
amz run entity.product.cosmo --param asin=B0GYFRH1L9
amz run entity.product.material --param asin=B0GYFRH1L9
amz run entity.product.copyability --param asin=B0GYFRH1L9

# 市场解决方案分类；需要全样本特征覆盖时再调用市场 COSMO
amz run entity.market.summary --param term="portable blender" --param marketplace=US
amz run entity.market.cosmo --param term="portable blender" --param marketplace=US --param pages=1 --param min_success=3

# Product 的主力词；Keyword 的特征和趋势
amz run entity.product.primary_keywords --param asin=B0GYFRH1L9
amz run entity.keyword.metrics --param term="portable blender" marketplace=US category=
amz run entity.keyword.trends --param term="portable blender" marketplace=US category=

# Market 竞品、画像和机会
amz run entity.keyword.products --param term="portable blender" marketplace=US category=
amz run entity.keyword.market_profile --param term="portable blender" marketplace=US category=
amz run entity.keyword.market_opportunity --param term="portable blender" marketplace=US category=

# 确定性计算（无需网络）
amz run entity.product_draft.set_facts --param draft_id=demo 'facts={"title":"a b c"}'
amz run entity.product_draft.listing_diff --param draft_id=demo new_text="a x c"
```

其余公开能力（COSMO、需求评估、创新评估、市场缺口、进入时机、材质门槛、
类目树、Rufus、1688 供应商、SIF 广告漏斗等）都在 `references/capabilities.md`，
接任务时按关键词查索引，别凭印象选能力。

## 5. 垂类 Agent 路由

下列任务需要根据中间证据动态选择、循环或停止时，使用对应 Skill。Skill 是独立入口，
不会注册成 `amz capabilities` 中的 Python 能力。
在 V1 发布包中，按名称读取 `skills/<name>/SKILL.md`。

| 用户目标 | Skill | 关键 CLI 入口 |
|---|---|---|
| 安装 CLI、打开配置、设置 COSMO 图片或 API Key / Token | `amz-setup` | `amz setup --web`、`amz setup --status --json` |
| 验证未上架新品想法 | `amz-concept-check` | `entity.keyword.*`、`entity.product.voc` |
| 理解市场驱动、方案变化和用户场景 | `amz-market-insight` | `entity.market.summary`、按需 `entity.market.cosmo`、`entity.product.voc` |
| 判断现在入局是否错过需求窗口 | `amz-market-timing` | `entity.market.timing` |
| 改写 Listing 名称、商品亮点和五点 | `amz-listing-rewrite` | `entity.product.listing_rewrite`、`entity.product.listing_part_rewrite` |
| 从一批竞品生成产品改进提案 | `amz-product-improve` | `entity.market.proposals` |
| 检查法规、类目和 FBA 准入 | `amz-risk-entry` | `entity.product.product_details` + 当前官方来源 |
| 快筛专利、商标、版权和授权 IP | `amz-risk-ip` | `entity.product.copyability` + 官方 IP 数据库 |
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
| `ERROR_LLM` | LLM 调用失败 | 核查豆包 Key、模型权限及响应；不要自动转用其他收费模型 |
| `ERROR_MISSING_FIELDS` | 必需业务事实或有效证据不足 | 读 `meta.missing`；补真实证据后重试 Entity，不填占位值 |
| `ERROR_CACHE_MISS` | 指定缓存未命中 | 允许取数时改走 Entity ensure；只读场景直接报告缺失 |
| `ERROR_NOT_FOUND` | 能力不存在/资源缺失 | 检查能力 ID |
| `ERROR_SERVER_INTERNAL` | SDK 未预期异常 | 保留 capability 和 message，停止盲目重试 |

## 7. 注意点

- **慢端点**：`product.get`、`entity.product.product_details` 首调 10-30s，bash 超时给足 60s+
- **API Key 配置**：交给 `amz-setup` Skill 打开本机安全页面。不要要求普通用户输入命令，
  也不要让用户把密钥发到聊天中。发布包不包含任何 API Key
- **模型分档**：内置 Analysis 默认统一使用豆包；COSMO 图片按比例缩到最长边 512 像素，与 Listing 一起交给 Lite 直接抽取；不单独做 OCR。
  常规聚合和相关性判断沿用 Lite，深度诊断、产品比较和完整 Listing 改写等原有 Pro 任务保留 Pro。
  一个豆包 / Ark Key 即可使用三档；无 Key 或调用失败时明确报错，不自动切其他模型服务。
- **COSMO 图片开关**：让 `amz-setup` 打开配置页，统一控制全部主图、附图及 A+ 图。默认关闭；关闭时只分析文字，修改后下次抽取重算缓存。
- **缓存**：`~/.cache/amz-cli/`（实体缓存 + 任务工作区）；`amz task cleanup` 定期清理
- **环境自检**：报错先跑 `amz doctor`；命令不存在时按“安装检查”执行 Skill 自带安装器
- **索引版本**：以当前 Skill 的 `references/capabilities.md` 为快速索引；完整 schema
  始终以已安装 CLI 的 `amz capabilities --id <id>` 为准

## 参考

- `references/capabilities.md` — 能力全索引（自动生成）
- `references/routes.md` — 原有业务的正式入口、兼容名称及适用输入
- `skills/<name>/SKILL.md` — 垂类 Agent 的动态编排说明
- `README.md` — CLI-first 接入细节
