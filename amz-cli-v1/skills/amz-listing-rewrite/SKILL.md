---
name: amz-listing-rewrite
description: 改写 Amazon Listing 的商品名称、商品亮点和五点描述，按 75/125 字符规则处理关键词、特殊字符及其他品牌词。适用于全量改写和局部调整。
---

# Amazon Listing 改写

## 准备与入口

有 ASIN 时调用 `entity.product.*` 方法，Entity 自动取得本品事实；不把竞品信息补成本品事实。没有 ASIN 或用户提供完整文案时，先用 `entity.product_draft.set_facts` 保存明确的用户事实，再调用同名 `entity.product_draft.*` 方法，草稿例子见 `../amz/references/routes.md`。

- 全量改写：`entity.product.listing_rewrite`，传 keywords 和可用的 feedback、title_differentiation。
- 插入关键词：`entity.product.listing_micro_insert`，传 insert_plan；亮点所需词放 insert_plan.title_differentiation。
- 单独修改：`entity.product.listing_part_rewrite`，part 为 title、bp1–bp5 或 title_differentiation；亮点模式传已确认的配套 draft_title 和现有 title_differentiation。
- 分配关键词：`entity.product.listing_allocate`；当前只分配 Title/BP1–5，同时安排亮点时使用全量改写。

需要先识别语义遗漏时调用 `entity.product.cosmo` 或 `keyword_gap`。参数以 `amz capabilities --id <id>` 为准。任务结果不覆盖原商品详情，也不自动发布。缺事实时报告缺项，不调用内部 Analysis 绕过。

## 发布规则

规则核对日期：2026-09-16。以目标站点及商品类型的当前规则为准。

- **商品名称**：非媒介类最多 75 个字符，空格计入；保留本品品牌、产品类型和关键识别信息，不为了 S 级关键词突破上限。
- **商品亮点**：独立字段 `title_differentiation`，最多 125 个字符，空格计入。用逗号分隔短语，提供有依据的材质、建议使用场景和关键规格。它不是五点描述，不把二者合并。
- 亮点可在搜索结果和详情页面中随商品名称显示并被搜索；是否可提交及展示以目标商品类型 schema 为准。名称超过 75 字符时不能同时提交亮点。
- **禁用字符**：`! $ ? _ { } ^ ¬ ¦`，只有这些字符属于已确认的本品品牌名称时例外。标题和亮点都按此标准检查。
- **品牌约束**：按用户要求，文案中不出现其他品牌或商标词；包括来自原文、关键词、兼容性说明的其他品牌。将已知词传入 `forbidden_terms`。不把“未匹配禁用词”称为完整商标审查。
- **媒介类例外**：不能推断它没有上限。核实具体类目规则后才传 `media_title_limit`；未经核实使用保守的 75 字符草稿，并说明范围。
- 规则优先于保留原文、最小改动和关键词分级；不编造功能、材质、认证或效果。

官方来源：[商品标题更新公告](https://sellercentral.amazon.com/seller-forums/discussions/t/ac660707-60c7-43e3-a3fd-420d7321cc4e)、[SP-API 模块化标题](https://developer-docs.amazon/sp-api/lang-en_EN/docs/submit-modular-titles)。官方说明于 2026-07-27 开始逐步推行；部分长标题提交仍可能被接受并由目录拆分，不能把 API 接受等同于满足本任务的 75/125 标准。禁止其他品牌是本任务采用的编辑要求，不据此宣称所有兼容性商标提及都被 Amazon 一律禁止。

## 交付与失败处理

交付商品名称、独立商品亮点、五点及名称/亮点字符数。标出删去的其他品牌词和仍缺证据的内容。

底层对长度、禁止字符和已知禁用词做确定性校验，违规返回 `ERROR_LLM`。修正反馈后最多重试两次；仍失败则报告具体问题，不截断文本冒充合格输出。对未知品牌、事实依据和媒介类规则仍需语义复核。
