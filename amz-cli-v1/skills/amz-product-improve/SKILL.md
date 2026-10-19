---
name: amz-product-improve
description: >
  从一组同类 Amazon ASIN 中找出下一代产品的改进机会。以 Product Entity 的
  strengths、weaknesses 和 use_insights 为主证据，再调用现有市场成功因子、缺口分析和
  微改造能力，输出可执行的产品提案。用于产品改进、竞品评论归纳、微改造和“做一个更好的
  XX”；不用于单品值不值得卖、完整 PRD 或概念图生成。
metadata:
  short-description: 从 Product VOC 聚合产品改进机会
---

# Amazon 产品改进

本 Skill 只负责编排和综合判断。产品详情、评论、VOC 与市场级推理都使用 amz-cli 的正式能力。

## 输入

- `asin_list`：必填，建议 3-20 个同一细分市场、相近价格带的 ASIN。
- `niche`：建议提供，用于报告标题和判断 ASIN 是否同类。
- 用户约束：可选，如目标成本、不能改模、目标人群或材料限制。

只有关键词时，先用 `entity.market.summary` 取得已有的方案分类，再用 `entity.keyword.products`
读取候选数值信息，筛掉用途、价格带或产品形态不一致的项。
不要因为搜索结果相邻就把不同细分市场合并。

正式入口和兼容名称见相对本 Skill 目录的 `../amz/references/routes.md`。

## Product Entity 主链

每个 ASIN 的正式入口是：

```bash
amz run entity.product.voc --param asin=<ASIN>
```

该入口会按 Entity 规则自动补齐详情和评论，并返回：

- `strengths`：Listing 事实中的创新与竞争优势。
- `weaknesses`：评论痛点、未满足需求和整体满意度背景。
- `use_insights`：使用场景、用户画像和购买动机。

不要再调用旧 `amz-api` 脚本，不要读取旧 `product_dev_v2` 管线，不要建立 Skill 私有缓存。
Entity 已处理依赖、TTL 和写回。

批量调用和市场聚合可直接运行薄封装：

```bash
amz python "<本 Skill 安装目录>/scripts/run.py" <ASIN1> <ASIN2> <ASIN3> --term "<市场关键词>"
```

脚本只调用公开 registry 能力，不含取数、分析提示词或缓存实现。结果较大时可用 `--out FILE`。
将路径解析成实际绝对路径后执行，用户的工作目录无需切换到 Skill 目录。

## 市场聚合

调用 `entity.market.proposals`，提供 term、marketplace 和明确的 sample_refs。Market 自动补齐 Product 评论/VOC，检查至少 3 个商品有真实评论与有效痛点，再生成本次缺口、成功因子和提案。结果包含 success_factors、market_gap 与 evidence，直接复用，不再重复调用分析。

只需要中间结论时，可单独调用 `entity.market.success_factors` 或 `entity.market.gap`。这些均由 Entity 检查证据；不手工拼装 strengths/weaknesses 字典，不直接调用 Analysis。
如果弱点证据太少，先检查 `satisfaction_context`。高满意度商品的少量差评不能被放大成市场共性。
确有需要时，按 ASIN 补 `entity.product.wishlist`，但它是辅助证据，不能替代真实问题频次。
只需要未满足需求时，读取已有 `weaknesses.unmet_needs`；未生成弱点时可用
`entity.product.unmet_needs` 自动补齐。不要再为同一需求调用一轮模型。

用户同时要求现有方案的材质可行性或复制壁垒时，按需用 `entity.product.material`、
`entity.product.copyability`；不要调用旧 `entity.product.innovation` 再重复评估。
两者只分析已有商品事实，不能证明新提案的工艺、成本或专利可行性。

## 动态判断

- 有效评论/痛点证据商品少于 3 个：停止市场分析，报告缺项；成功返回数不能替代有效证据商品数。
- 某问题只出现在 1 个 ASIN：标为单品问题，不冒充市场缺口。
- 优势与弱点冲突：保留满意度背景，说明这是取舍、品控波动还是结构缺陷。
- 建议不符合用户成本或工艺限制：删除或降级，不保留空泛方向。
- ASIN 之间用途明显不同：停止聚合，并列出应拆分的子市场。

## 提案门槛

每条提案必须同时包含：目标痛点、相关 ASIN、具体改动、适用场景、预期收益、难度和验证方法。
优先低到中难度的结构、材质、附件、规格、包装或说明改动。不要把“提升质量”“优化体验”当提案。
专利、合规和供应链可行性只标为待验证，不在本 Skill 中给最终结论。

## 输出

输出中文 Markdown 报告：

1. 市场总结与数据覆盖。
2. 头部成功因子及对应 ASIN。
3. 市场遗留问题，区分结构性问题、品控问题和说明问题。
4. 使用场景、人群和购买动机的交叉洞察。
5. 按“机会高、难度低”排序的 5-10 条微改造提案。
6. 每条提案的验证方法与停止信号。
7. 失败 ASIN、缺失字段和置信度。有效样本足够但部分商品失败时，保留结果并标为 `PARTIAL`，同时列出失败清单；不能声称全部样本成功。

报告中的频次、评分和引用必须来自能力结果。不要虚构评论原文。
