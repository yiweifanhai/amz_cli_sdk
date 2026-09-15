---
name: amz-risk-ip
description: >
  快速筛查 Amazon 商品的知识产权风险，包括外观专利、实用专利、商标、版权和授权型 IP。
  支持 ASIN、关键词、产品描述或图片；ASIN 优先读取 Product Entity 的详情与创新可复制性，
  再用官方数据库核对风险信号。用于侵权、专利、商标、版权、投诉风险和 IP 环境快筛；
  不把快筛当成 FTO 法律意见，也不处理法规或平台准入。
metadata:
  short-description: 快筛 Amazon 商品的专利、商标与版权风险
---

# Amazon IP 风险快筛

目标是发现需要停止、改设计或进入正式检索的信号。没有检索结果不等于没有权利。

## Product 数据路径

有 ASIN 时先调用：

```bash
amz run entity.product.product_details --param asin=<ASIN>
amz run entity.product.copyability --param asin=<ASIN>
```

第一项提供 Listing、品牌、图片、类目和结构描述；第二项只提供专利、供应链、技术与品牌壁垒的
初筛信号。`entity.product.copyability` 不是专利检索结果，不能单独支持“无专利风险”。
旧 innovation 是该结果的兼容投影，不重复调用；入口映射见 `../amz/references/routes.md`。

需要了解市场是否被单一品牌或授权 IP 控制时，可读取 `entity.product.competitors`，再选 3-5 个
代表商品核对品牌、形态和声明。不要批量调用无关 ASIN 来堆数量。

没有 ASIN 时，用用户提供的图片和描述建立临时事实，不要伪造 Product Entity。

## 检查顺序

1. 扫描具体权利信号：专利号、patented、patent pending、注册商标、官方授权、版权声明和角色名。
2. 区分购买动机：用户买的是功能，还是品牌、角色、图案或授权身份。
3. 判断外观是否具有非功能性的独特整体视觉；只有通用形状不能自动判低风险。
4. 判断功能是否依赖具体机构、连接、控制或工艺，而不只是抽象用途。
5. 按 [references/official-sources.md](references/official-sources.md) 搜索专利、商标和版权记录。
6. 对发现的权利核对权利人、目标市场、权利状态、相关性和当前证据日期。

只用名称搜索不能完成商标清查；只用标题关键词不能完成外观专利检索。图片相似度只能筛候选，
不能判断侵权。

## 分级与停止

- `HIGH`：发现与核心结构或整体外观高度相关的有效权利，或商品价值明显依赖未授权的知名 IP。
- `MEDIUM`：有相关权利或品牌生态信号，但保护范围、状态或产品差异仍需正式检索。
- `LOW`：基于已执行的检索只发现通用方案，且没有明确品牌、角色或专利声明。
- `UNKNOWN`：图片、权利状态、申请人或目标市场数据不足。

只有 `HIGH` 才在快筛 JSON 中设置 `stop=true`。`LOW` 不是安全保证；投入模具、采购或上架前，
对独特结构和外观仍应做正式检索。

本 Skill 不调用另一个 Skill。需要深查时，在本报告中给出已知专利号、搜索词、品牌、图片和风险类型，
建议用户单独调用 `patent-analysis`，避免隐式扩大法律分析范围。

## 输出

先给中文 Markdown 快筛报告，再附一个合法 JSON 对象：

```json
{
  "block": "ip_risk",
  "score": 0,
  "stop": false,
  "score_reason": "string",
  "data": {
    "risk_level": "LOW|MEDIUM|HIGH|UNKNOWN",
    "design_patent_risk": "LOW|MEDIUM|HIGH|UNKNOWN",
    "utility_patent_risk": "LOW|MEDIUM|HIGH|UNKNOWN",
    "trademark_risk": "LOW|MEDIUM|HIGH|UNKNOWN",
    "copyright_license_risk": "LOW|MEDIUM|HIGH|UNKNOWN",
    "known_rights": [],
    "searches_performed": [],
    "missing_checks": [],
    "recommended_next_step": "string",
    "checked_at": "YYYY-MM-DD"
  }
}
```

每个已知权利至少记录编号、权利人、来源 URL、状态证据、相关性理由和待确认项。报告末尾明确写：
“这是商业风险筛查，不是法律意见或 FTO 结论。”
