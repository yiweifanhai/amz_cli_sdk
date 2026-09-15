---
name: amz-market-timing
description: >
  评估 Amazon 商品现在进入市场是否赶得上需求窗口。给定 ASIN，可选关键词和上市周期，
  使用 Product Entity 获取商品事实、Keyword Entity 获取真实趋势，再调用
  analysis.market.timing 生成 GO、CAUTION 或 STOP。用于季节性、旺季、是否入局太晚、
  上架窗口等请求；不评价利润、产品力、合规或 IP。
metadata:
  short-description: 判断 Amazon 市场进入窗口与季节性
---

# Amazon 市场进入时机

## 默认假设

- 市场为美国，按北半球季节判断。
- 从决策到可售默认 3 个月。用户给出自己的周期时，以用户输入为准并在结论中说明。
- 使用执行当天的真实日期，不写死年份。

## 调用链

先读相对本 Skill 目录的 `../amz/references/capabilities.md`。`analysis.market.timing`
已直接使用重构后的 Market 实现，继续使用同一公开 ID。获取产品事实和主力词：

```bash
amz run entity.product.product_details --param asin=<ASIN>
amz run entity.product.primary_keywords --param asin=<ASIN>
```

用户给了明确目标词时直接使用；否则取主力词中与产品核心用途最一致的词，不机械取第一项。
再获取趋势：

```bash
amz run entity.keyword.trends --param term="<keyword>" marketplace=US
```

把 Product 详情、关键词趋势、当前日期和用户的上市周期交给
`analysis.market.timing`：日期传 `current_date`（YYYY-MM-DD），准备月数传
`preparation_months`（整数 0–24，默认 3），不能只在最终文案中改周期。两次以上能力调用应放进一个 `amz python` 脚本，避免重复启动和
手工转义嵌套 JSON。`requires` 只描述依赖，不会替 Analysis 自动取数。

如果趋势获取失败，仍可基于产品功能和使用场景做低置信度判断，但必须标记
`trend_data_available=false`。如果产品是强节日品而节日日期每年变化，执行时核对当年日期。

## 判断约束

- 从核心功能推导使用场景，再推导具体高峰月份；标题没有季节词不代表非季节品。
- 趋势数据优先于常识。趋势与常识冲突时，展示冲突并降低置信度。
- 开售窗口与需求上升期重合为 GO；需等待 3-5 个月为 CAUTION；需等待至少 6 个月或错过
  强节日窗口为 STOP。非季节品通常为 GO。
- 结论只覆盖时机，不把销量、利润或准入风险混入分数。

## 输出

先给简短中文结论，再附一个合法 JSON 对象：

```json
{
  "block": "market_timing",
  "score": 0,
  "verdict": "GO|CAUTION|STOP",
  "verdict_reason": "string",
  "details": {
    "product_function": "string",
    "use_case_inference": "string",
    "seasonality_type": "A|B|C|D",
    "seasonality_label": "string",
    "peak_demand_window": "具体月份",
    "launch_window": "YYYY-MM",
    "mismatch_reason": "string",
    "keyword": "string",
    "trend_data_available": true,
    "confidence": "high|medium|low"
  }
}
```

`score` 为 0-100 整数。不要只写“旺季”或“淡季”，必须写月份。
