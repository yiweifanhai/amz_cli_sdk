---
name: amz-novelty
description: >
  判断已上架 Amazon 商品是不是真创新、值不值得跟进：拿它和更早上架的同类老品比主图和五点，
  判断是否已有同样做法，给出创新类型（原理形态/功能/场景/人群/外观材质/情绪价值）、买家价值、
  0–100 创新分和逐步打分理由，并输出结构化 JSON。用于“这个产品创新吗”“是不是新方案”
  “以前有没有人做过”“这个新品值不值得跟”“给这批新品打创新分/筛创新品”等请求；
  不用于未上架概念（用 amz-concept-check）、整个市场的创新方向（用 entity.market.solution_evolution）、
  专利或侵权结论（用 amz-risk-ip）。
metadata:
  short-description: 单品创新度判定与值得跟进的创新筛选
---

# Amazon 单品创新度判定

目标：从新品里筛出值得跟进的创新，并说清它新在哪，供在它的方案基础上开发产品。
结论和分数全部来自 `entity.product.novelty`；本 Skill 负责调用、解读和固定格式输出，
不自行加减分。

## 输入

- 必填：美国站 ASIN。批量时逐个 ASIN 调用。
- 可选：`terms`，1–3 个核心英文关键词。用户知道核心词、或反查主词失败时传入。
- 可选：`as_of`（回测日期，YYYY-MM-DD）。

不追问。只有返回缺主关键词或缺老品时，才问用户要核心词。

## 调用

只调用 Entity，不直接调用 Calc、Analysis 或 Data：

```bash
amz run entity.product.novelty --param asin=<ASIN>
amz run entity.product.novelty --param asin=<ASIN> --param 'terms=["<core term 1>","<core term 2>"]'
```

常用参数：`pages`（每个词取样页数，默认 2，最多 3）、`max_groups`（比较组数，默认 6，最多 12）、
`per_group`（每组代表老品数，默认 3）、`min_lead_months`（老品至少早于本品上架的月数，默认 6）、
`solution_search=false`（关闭方案词召回）。完整参数以
`amz capabilities --id entity.product.novelty` 为准。

冷缓存单个 ASIN 约 5–11 分钟（逐组看图比较）。批量前告诉用户预计耗时。

## 判定口径（向用户解释时使用）

**老品**：比本品上架早至少 6 个月的商品；本品缺上架日期时，改用评估日往前 12 个月。
晚于本品或同一波上架的商品不算老品，避免同一波新品互相判成“已有方案”。

**老品来源**：
1. 主关键词搜索前 2 页，按标题分成方案组。本品所在组优先，其余按老品销量排序，每组取销量最高的代表老品。
2. 方案词召回：按本品核心做法另写搜索词，不设销量门槛，补上“做过但没卖起来”的早期同方案商品。

**打分三步**（同一组老品内）：
1. 基础分看最大的亮点：小改 25、明显不同 55、完全不同 80。
2. 加分：每多一个明显亮点 +8（最多 +16）；买家会主动找 +4。
3. 封顶：买家基本不在乎 30、兴趣有限 60；IP 周边 20、加量凑套装 20、简化降配 30、
   改成某型号专用 50、节日季节款 50；和老品是同一种做法只是小改 60。

有同方案组时，取同方案组里的最低分；否则取各组最低分，因为最接近的老品决定了它有多新。
形态、功能、场景、人群任一明显不同，记为改良款，不按同方案封顶。

## 读结果

`data` 中的关键字段：

| 字段 | 含义 |
|---|---|
| `innovation_score` | 最终创新分 0–100 |
| `existing` | 是否已有同样做法的老品 |
| `existing_matches` | 同方案老品；`existing_hot` 卖起来了，`prior_attempt` 做过但没卖起来 |
| `upgrades` | 同方案但明显改良的老品对照 |
| `primary_innovation` | 最强创新，如“场景创新·场景迁移” |
| `innovations` | 相对最接近老品的逐条创新点：维度、模式、等级、图文依据 `evidence`、常识解读 `insight` |
| `buyer_value` / `buyer_value_reason` | 买家价值 0–3 及理由 |
| `flags` | 非创新标记及依据 |
| `explanation` | 打分理由：用哪组的原因、基础分、每项加分、每条上限及是否生效、一句话算式 |
| `sample`、`limitations` | 搜了什么、比了几组几件、跳过和失败原因 |

参考分档（经验值，尚未经大样本回测）：≥70 值得跟进研究；50–69 已有做法的明显改良或买家兴趣一般，观察；
<50 换皮、凑套装、IP 周边或降配，不建议跟。

## 输出

每个 ASIN 依次输出：

1. 一句话结论：分数、分档、最强创新、是否已有方案。
2. 打分算式：原样展示 `explanation.summary`。
3. 打分明细表：基础分、每项加分、每条上限（标明是否生效），每行附理由和依据，取自 `explanation`。
4. 创新点：逐条列出 `innovations`，写清“新在哪、依据、对买家意味着什么”，作为跟进开发的参考。
5. 老品对照：同方案老品与改良款，带 ASIN、上架日期、月销量。
6. 覆盖范围与局限：比了几组几件、跳过原因；明确说“未发现同方案只限于实际比较的样本”。

最后附结构化 JSON（批量时为数组），字段直接取自返回结果，不改写数值：

```json
{
  "asin": "B0XXXXXXXX",
  "innovation_score": 84,
  "tier": "值得跟进研究",
  "existing": false,
  "primary_innovation": "人群创新·人群迁移",
  "buyer_value": 3,
  "buyer_value_reason": "…",
  "flags": [],
  "innovations": [{"label": "人群创新", "pattern": "人群迁移", "level": 3, "evidence": "…", "insight": "…"}],
  "existing_matches": [],
  "upgrades": [],
  "explanation": {"closest_group": "…", "selection_reason": "…", "base": {}, "bonuses": [], "uncapped_score": 92, "caps": [], "final_score": 84, "summary": "…"},
  "coverage": {"market_terms": ["…"], "compared_group_count": 6, "skipped_groups": [], "failed_refs": []}
}
```

`tier` 按上面的参考分档填写；`coverage` 取自 `sample` 的同名字段。批量时先给一张汇总表：
ASIN | 分数 | 分档 | 最强创新 | 已有方案 | 买家价值，按分数从高到低排序。

## 失败处理

- `ERROR_MISSING_FIELDS: legacy_products`：没有可比的早期商品。查看返回的 `sample`，向用户要核心词后用 `terms` 重跑；不要据此说“首创”。
- 缺主关键词或缺市场：向用户要 1–3 个核心词，用 `terms` 重跑。
- 缺本品五点或主图：说明无法判定，不用标题猜。
- `ERROR_LLM` / `ERROR_UPSTREAM`：如实报告失败，可稍后重试一次，不要编造结果。

## 边界

- 分数、类型和理由只来自 Entity 输出，不凭常识另行加减分。模型的常识判断已写在 `insight` 和 `buyer_value_reason` 中。
- `existing=false` 不等于全网首创，也不等于没有专利风险；需要时转 `amz-risk-ip`。
- 创新分衡量“新且买家在乎”，不代表利润、需求规模或供应链可行。要验证需求，再看本品和老品的
  `entity.product.voc`；要找改进方向，用 `amz-product-improve`。
