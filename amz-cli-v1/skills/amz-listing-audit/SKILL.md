---
name: amz-listing-audit
description: >
  审查已上架（尤其是新品）Amazon Listing 的硬伤：按标题、五点、主图、副图、A+、描述
  逐部分打分并给出可核对的证据——关键词数据、同方案竞品与同期新品怎么写、真实买家是谁。
  用于“帮我看看这条链接哪里有问题”“review 员工做的 Listing”“Listing 打分/体检/诊断”
  “主图人群对不对”“关键词埋没埋对”等请求；不用于直接改写文案（改写用 amz-listing-rewrite）、
  未上架概念验证（用 amz-concept-check）或利润、合规与专利结论。
metadata:
  short-description: 新品 Listing 分部分审查与硬伤举证
---

# Amazon Listing 审查

目标：找出这条 Listing 必须改的问题，每条都能拿给写它的人核对。证据是"原因级"的：
这个词搜索和成交都大却没埋、竞品 N 个里 M 个都写了、主图展示的人群与评论里的真实买家不符；
不是"排名靠后"这种结果。

## 输入

- 必填：ASIN（美国站）。批量时逐个 ASIN 审查。
- 强烈建议：1–3 个核心关键词 `terms`。新品反查词少于 5 个时 Entity 会返回
  `ERROR_MISSING_FIELDS: terms`，此时问用户要核心词，**不要自己猜**。
- 可选：`benchmark_asins`（用户点名的竞品，最多 5 个）、`brief`（产品要解决的问题、目标人群、
  相对竞品的优势，原话传入）、负责员工（只用于汇总表，不传给 Entity）。

开始前最多问 2 个问题：核心词是什么；这款产品想卖给谁、主打什么优势。用户说"直接跑"就不问。

## 调用

只调用 Entity，不直接调用 Calc、Analysis 或 Data：

```bash
amz run entity.product.listing_audit --param asin=<ASIN> \
  --param 'terms=["<core term 1>","<core term 2>"]' \
  --param brief="<用户原话：人群/要解决的问题/优势>"
```

常用参数：`benchmark_asins`、`pages`（每个核心词取样页数，默认 1）、`peer_months`（同期窗口，默认 6）、
`include_visual=false`（只审文案时）。完整参数以 `amz capabilities --id entity.product.listing_audit` 为准。

一次审查约 2–4 分钟（冷缓存），包含：拉竞品详情、竞品评论洞察、COSMO、多模态看图。
批量审查前告诉用户预计耗时。

## 读结果

返回 `ListingAuditOutput`：

- `report_markdown`：给人看的完整报告，**直接展示它**，不要重写或删减证据。
- `verdict`：red 必须返工 / yellow 限期整改 / green 可以微调。
- `sections[]`：每部分 `score`（满分 10，硬伤 -3、建议 -1）、`findings`（现状 / 对照 / 判断 / 改法 / 负责岗位）。
- `not_checked`、`limitations`：没检查到的项与原因。必须告诉用户，不能当作"没问题"。

批量时额外输出一张汇总表：ASIN | 负责人 | 结论 | 标题 | 五点 | 主图 | 副图 | A+ | 描述 | 硬伤数。

## 后续动作

- 文案问题需要出新稿时，转交 `amz-listing-rewrite`：缺的关键词传 `listing_micro_insert` 的
  insert_plan，或用 `listing_part_rewrite` 改指定部分，并把审查结论作为 feedback。
- 图片问题输出改图需求：哪张图、现在表达什么、应该表达什么、参考哪个竞品 ASIN。不要生成图片。

## 边界

- 分数和结论来自 Entity 的规则与证据；不要凭常识加分减分或补数据。
- `not_checked` 中的部分（例如 A+ 数据源未返回、评论服务失败）要明说"未检查"。
- A+ 为空不等于没做 A+，数据源可能漏抓，按报告原文提示用户人工确认。
- 本品自己的点击率、转化率卖家精灵查不到；用户提供后台 Search Query Performance 报表前，
  不要对本品转化率下结论。
