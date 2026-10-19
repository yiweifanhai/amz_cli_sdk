---
name: amz-market-timing
description: >
  评估 Amazon 商品现在进入市场是否赶得上需求窗口。给定 ASIN，可选关键词和上市周期，
  由 Market Entity 准备商品事实和真实趋势，再生成 GO、CAUTION 或 STOP。用于季节性、旺季、是否入局太晚、
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

先查 `entity.market.timing` 的 schema。用户给了明确关键词时使用该市场；只有 ASIN 时，先通过 `entity.product.primary_keyword_ref` 解析市场身份，并把 Product ref 作为 product_ref 传入。

```python
from amz import call, Code
from amz.schemas.entity_ref import product_ref

result = call("entity.market.timing", term=keyword, marketplace="US",
              current_date=current_date, preparation_months=preparation_months,
              product_ref=product_ref("US", asin).model_dump(mode="json"))
if result.code != Code.OK:
    raise RuntimeError(result.message)
```

current_date 使用执行当天的 YYYY-MM-DD，preparation_months 默认由本 Skill 明确传 3，用户提供周期时传其值（0–24）。Entity 自动准备 Keyword 趋势及可选 Product 详情。趋势获取失败、少于两个有效日期点或商品事实不足时停止，报告缺项，不回退到常识时机判断。

已有外部趋势时，仅通过 schema 定义的 trend_evidence 提供来源、观察日期、市场与日期值点；不伪造来源。日期随年份变化的节日仍需核对当年日期，不能把常识替代真实趋势。

## 判断约束

- 从核心功能推导使用场景，再推导具体高峰月份；标题没有季节词不代表非季节品。
- 所有月份与需求窗口判断必须受实际趋势支持。覆盖不足时明确说明限制，不把趋势外推写成已验证事实。
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

`score` 为 0-100 整数。有足够趋势证据时写具体月份，不只写“旺季”或“淡季”；样本周期不足时明确“当前数据不足以确定月份”，不得猜测峰值。
