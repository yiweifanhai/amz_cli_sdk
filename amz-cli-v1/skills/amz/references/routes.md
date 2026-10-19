# Entity 业务入口

Skill 只通过 Entity 或已注册 Composite 调用计算和分析业务。`calc.*` 和 `analysis.*` 是内部实现，普通 CLI、Python call、HTTP 和 MCP 不接受直接执行；内部旧 ID 只保留实现兼容。遇到旧调用，按下面映射改用 Entity，不拼空字典或调用开发测试入口绕过检查。

| 业务 | Entity 入口 | 输入与结果 |
|---|---|---|
| 商品 COSMO、材质、复制难度 | `entity.product.cosmo` / `material` / `copyability` | ASIN + marketplace，自动准备依赖并缓存字段 |
| 商品 VOC | `entity.product.voc` 或 `strengths` / `weaknesses` / `use_insights` / `praise` / `wishlist` | 评论任务必须有有效评论；空评论不算分析成功 |
| Listing 改写、插词、局部改写、分配关键词 | `entity.product.listing_rewrite` / `listing_micro_insert` / `listing_part_rewrite` / `listing_allocate` | 自动取本品事实，另传关键词和编辑要求；草稿不覆盖原 Listing |
| 新品与真实竞品比较 | `entity.product.compare` | `benchmark_refs` 为 3–5 个同站点真实 Product 引用 |
| 商品维度打标 | `entity.product.classify` | 显式 `dimensions`，本品事实由 Entity 读取 |
| 商品关键词相关性与覆盖 | `entity.product.keyword_relevance` / `keyword_gap` | 显式候选关键词，商品事实自动准备 |
| COSMO 的目标商品位置建议 | `entity.product.cosmo_classify` | `market_ref` 与采样参数；自动准备 Market COSMO |
| 关键词聚类、评分 | `entity.keyword.cluster` / `score` | 候选集；score 还必需目标 `product_ref`，不接收裸 product_info |
| 市场分类、COSMO | `entity.market.summary` / `cosmo` | term + marketplace + 采样参数 |
| COSMO 精确术语合并 | `entity.market.cosmo_merge` | 可传 `sample_refs` / `pages`；准备各 Product.cosmo 后保留 `terms/groups` 和位置计数，不做语义模型分组 |
| COSMO 按阈值和目标商品同义聚合 | `entity.market.cosmo_aggregate` | `min_count`、`model`，可传 `target_product_ref` 准备真实目标上下文；保留原 TermGroup 结果 |
| 市场成功因子、缺口、改造提案 | `entity.market.success_factors` / `gap` / `proposals` | term + marketplace，可指定 `sample_refs`；至少 3 个有有效评论证据的商品，proposals 自动生成并返回本次成功因子与缺口 |
| 市场时机 | `entity.market.timing` | 显式 `current_date`、`preparation_months`；自动补 Keyword 趋势，缺真实趋势就停止 |
| TACOS、关键词市场广告后利润 | `entity.market.tacos` | term + pages；自动读取 SIF ACOS 与 Product 反查词，输出 3/6/12 月累进/互斥分组。属于估算，不含采购成本；缺广告数据不填零 |
| 需求计算 | `entity.market.demand` | 带来源、观察日期和三年区间的 `google_evidence`；Entity 自动补 Amazon 月度同比和市场收入样本，或检查显式 `amazon_evidence` / `market_evidence`，缺必需证据就停止 |
| 主定价维度、其他决策维度 | `entity.market.primary_pricing_dimension` / `discover_dimensions` | 市场样本、候选 `keywords`，自动准备商品事实、价格带和词群 |
| 淘宝市场分类 | `entity.taobao_market.summary` | 淘宝 term，不混用 Amazon 商品身份 |

以上短名称均在该行前缀之下。参数结构以 `amz capabilities --id <完整 ID>` 为准。

## 引用与明确样本

Product 引用由工厂生成，不手拼站点或创建假 ASIN：

```python
from amz import call, Code
from amz.schemas.entity_ref import product_ref, EntityRef

refs = [product_ref("US", asin).model_dump(mode="json") for asin in asins]
result = call("entity.market.proposals", term=keyword, marketplace="US", sample_refs=refs)
if result.code != Code.OK:
    raise RuntimeError(result.message)
```

只有 ASIN 而没有目标市场关键词时，读取 `entity.product.primary_keyword_ref`，用 `EntityRef.model_validate(result.data).identity` 得到市场身份参数。该 Ref 的 JSON 只有 entity_type/key，不直接包含 identity。

`sample_refs` 代表本次明确商品集合，不改变 Product 的主市场归属。对失败、空结果和有效数据分别处理；不能用成功返回数代替有证据的商品数。

COSMO 的 `cosmo_merge` 和 `cosmo_aggregate` 是独立任务方法，不等同于持久字段 `cosmo`。它们自动补齐 Product.cosmo 并复用有效单品缓存，附 `evidence` 中的使用/失败 refs、源时间和最小成功数；不接受调用方拼接 `cosmo_outputs`。省略 pages 保留已选 Market 样本，显式 sample_refs 不改 Market 的长期样本。旧 `analysis.cosmo.merge/aggregate` 分别迁到这两个入口，不能改成统一调用 `entity.market.cosmo` 丢掉参数和结果字段。

## 没有 ASIN 的新品或已有文案

使用本地 `ProductDraft`，不建立假的 Product。先创建有明确本地名称的草稿事实，再调用它的业务方法：

```python
from amz import call, Code

saved = call("entity.product_draft.set_facts", draft_id="bottle-concept", facts={
    "marketplace": "US", "title": "A reusable water bottle",
    "bullet_points": ["User supplied, confirmed product feature"], "source": "user",
})
if saved.code != Code.OK:
    raise RuntimeError(saved.message)
result = call("entity.product_draft.listing_rewrite", draft_id="bottle-concept", keywords={"S": ["water bottle"]})
```

`ProductDraft.compare` 同样要求 3–5 个真实竞品引用。源事实来自用户，输出仍是建议或草稿，不视为已售商品事实。草稿不是 Amazon EntityRef；通过 draft_id 访问。

## 失败与结果

Entity 负责补依赖及数据检查。缺必需证据返回具体缺项；上游失败保留错误，不回退为常识结论，不用 `[]`、`{}`、`unknown` 填充绕过。真实没有发现痛点时报告缺少提案依据，不要求模型强行产生机会。

字段能力复用 TTL 缓存；带样本/比较对象/日期/编辑要求的 task operation 不缓存结果，复用底层字段缓存。提案输出包含本次成功因子和缺口，不重复调用三套分析。

Keyword.score 会补取候选词的四维指标；只有 search_volume、PPC 和 conversion_rate 仍可能不足。按错误中的逐词缺项报告，不把 PPC 当作竞争指标，也不补默认 5 分。

## 确定性计算

Calc 也属于内部实现。旧 `calc.*` 调用应迁移到下列 Entity；普通 CLI、Python call、HTTP、MCP 和 Composite 都不接受 Calc 直调。

| 计算 | 正式入口 | 调用条件 |
|---|---|---|
| FBA 费用、毛利率、资金回报 | `entity.product.fba_fee` / `margin` / `return_on_capital` | Product 自动准备价格、包裹数据；显式成本与日期属于任务参数 |
| 主力词、Listing 覆盖 | `entity.product.primary_keywords` / `keyword_gap` | 自动准备反查词或当前 Listing |
| 文案差异 | `entity.product.listing_diff` / `entity.product_draft.listing_diff` | 传 new_text 和 part；原文从实体读取 |
| 满意度、材质门槛 | `entity.product.satisfaction` / `material_eligibility` | 自动准备评论评分或材质结论 |
| 流量维度 | `entity.product.traffic_dimensions` | 传同站点 market_ref，价格带来自 Market 样本 |
| 市场统计、画像、机会分 | `entity.market.stats` / `profile` / `opportunity` | 使用 Market 当前样本，可显式传 pages |
| 需求分、COSMO 精确合并 | `entity.market.demand` / `cosmo_merge` | 延续前文证据模型与 Product refs 规则 |

已有完整数据也不能用内部测试接口绕过 Entity。收到缺项时恢复数据源或补用户真实任务条件，不传假价格、假评论或任意商品字典。
