---
name: patent-analysis
description: >
  对 Amazon 商品做正式的专利候选检索与风险证据整理。支持 ASIN、已知专利号、品牌、
  功能结构描述和产品图片；先用 Product Entity 建立商品事实，再在 USPTO 等来源检索
  实用专利、公开申请和外观专利，核对权利人、状态、期限与相关性。用于专利深查、
  FTO 前置研究、法律状态、同族和外观候选比对；结果不是律师的侵权或有效性意见。
metadata:
  short-description: 深查 Amazon 商品的专利候选与法律状态
---

# Amazon 产品专利深查

输出可复核的候选和证据链，供产品改版、停止决策或专利律师继续做 FTO。

## 输入与范围

优先收集：ASIN、目标销售国家、已知专利号、核心功能、关键结构、品牌或可能权利人、产品图片。
至少要有 ASIN、已知专利号或足够具体的产品结构描述之一。

默认只查美国。用户要求其他国家时，必须使用对应司法辖区的官方数据库并单独给结论，不能用
美国记录推断全球状态。

## 用 Product Entity 建立事实

有 ASIN 时调用：

```bash
amz run entity.product.product_details --param asin=<ASIN>
amz run entity.product.innovation --param asin=<ASIN>
```

提取标题、品牌、图片、五点、说明、规格、完整类目和所有专利声明。创新能力只用于生成结构词、
功能词和初始壁垒假设，不是检索结论。

如需比较市场形态，可调用 `entity.product.competitors` 后只选少量代表品。Product Entity 已负责
商品数据缓存；本 Skill 不维护第二套 ASIN 缓存。

## 检索路线

先读 [references/search-playbook.md](references/search-playbook.md)，按已有信息动态选路：

- 已知专利号：直接核对专利、申请、权利人、连续申请关系和状态。
- 已知品牌或公司：按申请人和受让人搜索，再用结构、功能和分类过滤。
- 只有产品：拆成品类词、结构词、功能词和替代说法，先宽搜，再加 CPC/USPC/Locarno 分类。
- 外观风险：使用干净主图和多个视角找候选，再逐项对比整体视觉印象和关键设计特征。

PatentsView 只在环境中已有 `PATENTSVIEW_API_KEY` 时使用，并发送 `X-Api-Key`。没有 Key 时直接使用
USPTO Patent Public Search 或已登录的专利数据库，不反复申请或降级成无来源结论。

第三方数据库、Google Patents 或智慧芽可用于发现和聚类候选。候选编号、权利人和美国法律状态
最终回到 USPTO 记录核对。登录态存在时可用浏览器操作智慧芽；不保存账号密码，也不依赖旧的
Playwright 选择器脚本。

## 状态与相关性核对

每个候选至少检查：

1. 文献类型：授权专利还是公开申请。
2. 权利人和受让链。
3. 目标国家是否有有效权利或相关同族。
4. 维护费、终止免责声明、期限调整、继续申请和审查历史等会影响状态的因素。
5. 权利要求或外观图与目标产品的具体对应点和差异点。

不要用“申请日 + 20 年”或“授权日 + 15 年”的简单算术替代法律状态核对。美国外观专利期限规则
可用于初步估算，但最终状态仍需官方记录。发现高相关有效候选时停止扩展性搜索，把时间用于核对
权利要求、差异和状态。

## 风险分级

- `CRITICAL`：高相关有效候选覆盖核心方案，且差异不足或存在明确维权证据。
- `HIGH`：有高相关有效候选，但保护范围或产品差异仍需律师判断。
- `MEDIUM`：有相关候选，状态、权利要求映射或目标国家覆盖不完整。
- `LOW`：执行了可复现的多路径检索，未发现高相关候选，但仍存在检索盲区。
- `UNKNOWN`：数据源、图片、检索词或状态信息不足。

只有律师可以给最终 FTO 或侵权意见。`LOW` 也不能表述为“安全”或“无专利”。

## 输出

先输出中文 Markdown 摘要，再附合法 JSON：

```json
{
  "asin": "string|null",
  "target_jurisdictions": ["US"],
  "analysis_timestamp": "ISO-8601",
  "product_facts": {"brand": "string|null", "functional_terms": [], "structural_terms": [], "images_reviewed": []},
  "search_log": [{"source": "string", "query": "string", "filters": {}, "searched_at": "ISO-8601"}],
  "candidates": [{
    "publication_number": "string",
    "kind": "utility|design|application|unknown",
    "title": "string",
    "owner": "string|null",
    "status": "active|pending|expired|lapsed|unknown",
    "status_source_url": "string",
    "relevance": "HIGH|MEDIUM|LOW",
    "matching_features": [],
    "different_features": [],
    "open_questions": []
  }],
  "overall_risk": {"level": "CRITICAL|HIGH|MEDIUM|LOW|UNKNOWN", "summary": "string", "recommended_action": "string"},
  "limitations": []
}
```

引用直接链接到专利或官方状态页。报告末尾明确写：本报告不是法律意见；进入模具、采购或上架前，
对 `CRITICAL`、`HIGH` 和无法消除的 `MEDIUM` 候选交由目标国家的专利律师审查。
