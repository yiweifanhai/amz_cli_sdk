# 正式入口与兼容映射

Analysis 重构保留原公开 ID，运行时注册到 `amz.analysis.product`、`market`、`keyword`、
`taobao_market` 中的正式实现。旧名称不代表旧算法，不能为同一输入重复跑两套分析。
Python 脚本通过 `amz.registry.invoke` 调公开 ID，不依赖旧模块的函数签名。

## 有 ASIN 或关键词时

| 用户要解决的问题 | 优先入口 | 与原调用的关系 |
|---|---|---|
| 商品文案/图片的 COSMO 语义 | `entity.product.cosmo` | 自动准备输入，再调用重构后的 `analysis.cosmo.extract` |
| 材质及开发难度 | `entity.product.material` | 自动准备输入，再调用 `analysis.material.assess` |
| 复制难度与壁垒 | `entity.product.copyability` | `entity.product.innovation` 仅是同一结果的兼容投影，不额外调用 |
| 商品优势、弱点和使用洞察 | `entity.product.voc` | 自动准备详情与评论，复用对应 Product Analysis；只需一项时调用 `entity.product.strengths`、`entity.product.weaknesses` 或 `entity.product.use_insights` |
| 只看未满足需求 | `entity.product.unmet_needs` | 从同一份 weaknesses 结果读取；已有 VOC 时直接用 `weaknesses.unmet_needs` |
| Amazon 市场方案分类、人群与场景 | `entity.market.summary` | 自动准备标题样本，调用 `analysis.market.classify`；标题只支持样本概述 |
| 市场 COSMO 特征及覆盖 | `entity.market.cosmo` | 自动准备 Product COSMO，调用 `analysis.market.cosmo`；返回样本、失败项、来源与覆盖分母 |
| 淘宝方案分类 | `entity.taobao_market.summary` | 自动准备淘宝样本，调用 `analysis.taobao.market_classify`；不使用 Amazon Entity 接收淘宝商品 |

只有 ASIN 而需要市场分析时，调用 `entity.product.primary_keyword_ref`，将返回 Ref 解析为对象后读取
`identity`。JSON 只包含 entity_type/key，没有 identity 字段：

```python
from amz import registry, Code
from amz.schemas.entity_ref import EntityRef

relation = registry.invoke("entity.product.primary_keyword_ref", {"asin": asin, "marketplace": "US"})
if relation.code != Code.OK:
    raise RuntimeError(relation.message)
identity = EntityRef.model_validate(relation.data).identity
summary = registry.invoke("entity.market.summary", identity)
if summary.code != Code.OK:
    raise RuntimeError(summary.message)
```

这里的 `asin` 使用用户已提供的值。已有明确关键词时直接用 `term` 和 `marketplace`。
取样和模型参数先查 `amz capabilities --id <id>`。

`entity.market.cosmo` 会处理所选页数内的全部商品，并不只处理报告里展示的代表品。
需要全样本特征覆盖时再调用，并明确 pages 与成功样本门槛；只研究少数指定 ASIN 时，
逐个调用 `entity.product.cosmo` 后用 `analysis.market.cosmo` 汇总显式样本。
Ref 用 SDK 的 `product_ref(marketplace, asin)` 工厂创建，来源/更新时间按实际数据填写。

## 已持有完整输入时

| 原有业务或名称 | 正式调用方式 |
|---|---|
| Listing 改写、插词、分配、局部修改 | 继续调用 `analysis.listing.rewrite`、`analysis.listing.micro-insert`、`analysis.listing.allocate`、`analysis.listing.part-rewrite`；这些 ID 已指向新 Product 实现 |
| 关键词相关性、意图聚类、评分 | 继续调用 `analysis.keyword.relevance`、`analysis.cluster.keywords`、`analysis.keyword.score`；显式候选不能被自动换成另一份关键词样本 |
| 多商品成功因素 | `analysis.market.success-factors`，输入各商品的 strengths |
| 评论中的市场缺口 | `analysis.market.gap-analysis`；旧 `analysis.market.gap` 注册到同一函数 |
| 产品改进提案 | `analysis.market.renovation-proposal`；旧 `analysis.market.proposals` 注册到同一函数 |
| 新品与基准品比较、进入时机、规格维度 | 保留对应 `analysis.innovation.compare`、`analysis.market.timing`、`analysis.asin.discover-dimensions`、`analysis.asin.primary-pricing-dimension`；它们已使用新实现，仍需完整任务上下文 |
| 多商品 COSMO 语义汇总 | 新任务用 `analysis.market.cosmo`，准备带 Product Ref、来源和时间的输入。旧 `analysis.cosmo.aggregate` 共用分组核心，但其 min_count/target_product 和旧输出结构不同，仅在调用者确需该格式时保留 |
| COSMO 确定性合并、关键词覆盖计算 | 用 `calc.cosmo.merge`、`calc.keyword.gap`；旧 `analysis.cosmo.merge`、`analysis.keyword.gap` 是计算兼容入口，不是额外模型分析 |

输入或输出结构不同的入口不能只替换 ID。市场 profile/opportunity 提供数值画像与机会分，
summary 提供标题分类，COSMO 提供 Listing 特征覆盖，gap-analysis 提供评论缺口；按研究问题取用。
已有 strengths/weaknesses/use_insights 时直接传给市场分析，不重新抓取或重复生成同一份 VOC。

## 版本与结果读取

- capability 的完整输入/输出 schema 以已安装 CLI 为准。兼容 ID 保留不代表所有字段永远不变。
- `primary_keyword_ref`、`product_refs` 等引用入口返回 Ref，解析后用对象的 `identity` 继续调用公开能力。
  旧 `entity.product.market` 仍返回 Market 投影，不能按 Ref 解析；新流程使用上面的主关键词引用。
- Listing 的 `title_differentiation` 是独立亮点，不能丢弃或拼回超长标题。
- VOC 的 positive_pct/negative_pct 为 null 时表示缺少全量星级分布，不是 0%。
- 当前 Analysis 使用豆包/Ark Key。旧用户只配置 DeepSeek 时需要通过配置页补豆包 Key。
- 宿主负责选路、检查证据和组织报告；SDK Analysis 仍执行实际模型调用与结果校验。
