---
name: amz-market-insight
description: >
  分析 Amazon US 细分市场的宏观驱动、近年解决方案变化和真实用户场景。
  给定关键词，可选 ASIN，结合 Keyword/Market Entity、代表商品的 Product VOC 与
  当前外部来源输出可供下游消费的结构化 JSON。用于市场洞察、市场理解、产品演变、
  用户场景和“为什么这个市场有机会”等请求；不替代利润、准入或专利分析。
metadata:
  short-description: 生成 Amazon 细分市场三维洞察
---

# Amazon 市场洞察

输出三个问题的答案：市场为什么存在，解决方案怎样变化，谁在什么场景下使用。

## 输入

- `keyword`：必填。只有 ASIN 时，先用 `entity.product.primary_keywords` 取得主力词。
- `asin`：可选。用于从单品进入市场并读取真实 VOC。
- `marketplace`：默认 `US`。

## 调用链

先读相对本 Skill 目录的 `../amz/references/routes.md`，按需查
`../amz/references/capabilities.md`。方案分类、人群与场景概述先使用正式市场分析：

```bash
amz run entity.market.summary --param term="<keyword>" --param marketplace=US
```

使用分类结果选择同类代表商品，不在宿主中重做相同标题分类。该结果只基于标题，不能代替评论证据。
需要价格带、品牌集中度等数值依据时，再按需调用：

```bash
amz run entity.keyword.market_profile --param term="<keyword>" marketplace=US
amz run entity.keyword.market_opportunity --param term="<keyword>" marketplace=US
amz run entity.keyword.products --param term="<keyword>" marketplace=US
```

用户提供 ASIN 时，可从 Product 直接进入市场：

```bash
amz run entity.product.market_profile --param asin=<ASIN> marketplace=US
amz run entity.product.market_opportunity --param asin=<ASIN> marketplace=US
amz run entity.product.voc --param asin=<ASIN>
```

从 `entity.keyword.products` 中选 2-5 个代表 ASIN，并按需调用
`entity.product.voc`。使用其中的 `strengths`、`weaknesses` 和 `use_insights`
校验主流方案、遗留问题和使用场景。不要重新实现评论分析。

用户需要比较商品特征、文案语义或市场覆盖时，使用 `entity.market.cosmo`；根据研究范围明确
`pages`（1–3）与 `min_success`。它会读取所选页数的全部 Product，不只是代表 ASIN。
只研究指定商品时，使用具有明确 product_refs 的 Market；通过 `entity.market.cosmo` 准备并分析该样本，不直接组装底层 Analysis 输入。
使用返回的 coverage_count、coverage_denominator、failed_product_refs 和 sources，
不把词条出现次数当商品覆盖，也不把未提及当功能不存在。

需要跨商品评论缺口时，调用 `entity.market.gap` 并传 sample_refs，由 Market 复用 Product VOC。至少 3 个有效评论证据商品；证据不足时停止，不拿数值机会分代替。

外部搜索只负责 Entity 没有覆盖的宏观变化与近 5-10 年解决方案变化。使用执行当天的
年份作为时间锚点，优先美国本地、官方、研究机构和可靠产品评测来源。市场可能增长、
稳定或衰退，不预设结论。所有外部事实保留 URL 和发布日期；过时或地区不匹配的数据降权。

## 动态选择

- 市场数据足够但外部趋势证据弱：保留用户与竞争结论，把宏观置信度设为低。
- 代表商品不是同一使用场景：继续筛选，不把相邻品类混成一个市场。
- Product VOC 互相冲突：保留分群差异，不强行合并成单一用户画像。
- CLI 返回部分失败：输出已有证据和失败项，不编造缺失字段。

## 输出

只输出合法 JSON，不加 Markdown 围栏。至少包含：

```json
{
  "keyword": "string",
  "asin": null,
  "marketplace": "US",
  "analyzed_at": "YYYY-MM-DD",
  "macro_environment": {
    "drivers": [{"name": "string", "evidence": "string", "source_url": "string"}],
    "risks": [{"name": "string", "evidence": "string", "source_url": "string"}]
  },
  "solution_evolution": {
    "recent_iterations": [{"period": "string", "change": "string", "pain_solved": "string", "evidence": "string"}],
    "current_mainstream": {"form": "string", "price_range": "string", "core_features": ["string"]}
  },
  "user_scenarios": {
    "scenarios": [{"who": "string", "when_where": "string", "goal": "string", "key_feature": "string", "evidence": "string"}],
    "core_insight": "string"
  },
  "selection_takeaways": ["string"],
  "data_quality": {"sufficient": true, "missing": [], "notes": null}
}
```

`drivers` 取 2-5 个，用户场景至少 3 个，选品结论取 2-4 条。没有证据的字段用 `null`
或空数组，并在 `data_quality` 说明，不使用空字符串充数。
