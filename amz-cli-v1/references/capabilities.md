# amz-cli 能力全索引

> 本文件由 `scripts/gen_capabilities.py` 自动生成，勿手改。生成时间：2026-10-19 15:56 UTC，共 **104** 个能力。

每个能力一行：ID + 用途 + 必填参数 + 前置依赖（`requires`）。
Skill 计算和分析业务调用 Entity 或 Composite；Data 仅供明确调试，Calc 和 Analysis 不公开。
需要完整可选参数与字段说明时，跑 `amz capabilities --id <id>`。
原有能力的正式入口与兼容名称见 [调用映射](routes.md)；同一任务不要重复调用兼容入口。

## 推荐入口：实体（entity）（82 个）

- `entity.keyword.aba_series` — 获取关键词 ABA 周排名序列（需 csv_path 指向 ABA CSV 文件） — lazy 按需填充 + TTL 回填（aba_file） 必填: `term`
- `entity.keyword.cluster` — 对显式候选或已有 related_keywords 做意图聚类，当前词作为主词 — lazy 按需填充 + TTL 回填（analysis.cluster.keywords） 必填: `term`
- `entity.keyword.market` — 获取该关键词的市场分析实体 — lazy 按需填充 + TTL 回填（entity.market） 必填: `term`
- `entity.keyword.market_opportunity` — 从 Keyword 直接获取 Market Opportunity；自动级联 Market 与 Stats — lazy 按需填充 + TTL 回填（entity.market.opportunity） 必填: `term` 依赖: `entity.keyword.market_stats`
- `entity.keyword.market_profile` — 从 Keyword 直接获取 Market Profile；自动级联 Market 与 Stats — lazy 按需填充 + TTL 回填（entity.market.profile） 必填: `term` 依赖: `entity.keyword.market_stats`
- `entity.keyword.market_stats` — 从 Keyword 直接获取 Market Stats；缺少 Market 时自动级联创建 — lazy 按需填充 + TTL 回填（entity.market.stats） 必填: `term` 依赖: `entity.keyword.market`
- `entity.keyword.metrics` — 获取关键词特征（core 字段刷新） — lazy 按需填充 + TTL 回填（/keyword-miner） 必填: `term`
- `entity.keyword.products` — 获取该关键词的竞品列表 — lazy 按需填充 + TTL 回填（/competing-lookup） 必填: `term`
- `entity.keyword.score` — 补齐目标商品和候选词四维评分指标；结果属于本次任务，不保存为全局分数 — Entity prepares required evidence; task result is not cached 必填: `term`, `product_ref`
- `entity.keyword.trends` — 获取关键词搜索量趋势时间序列（写入 self.trends） — lazy 按需填充 + TTL 回填（/seller-sprite/trends） 必填: `term`
- `entity.market.cosmo` — Aggregate verified Product COSMO results with explicit partial-failure coverage — lazy 按需填充 + TTL 回填（analysis.market.cosmo） 必填: `term` 依赖: `entity.market.product_refs`
- `entity.market.cosmo_aggregate` — Group Product COSMO terms with a count threshold and optional target Product facts — Entity prepares required evidence; task result is not cached 必填: `term`
- `entity.market.cosmo_merge` — Merge prepared Product COSMO into exact term and location counts without semantic grouping — Entity prepares required evidence; task result is not cached 必填: `term`
- `entity.market.demand` — Prepare real Google, Amazon year-over-year, and market sample evidence — Entity prepares required evidence; task result is not cached 必填: `term`, `google_evidence`
- `entity.market.discover_dimensions` — Prepare one sample and its primary price dimension before other dimensions — Entity prepares required evidence; task result is not cached 必填: `term`, `keywords`
- `entity.market.gap` — Find common gaps only after three Products supply actual review evidence — Entity prepares required evidence; task result is not cached 必填: `term`
- `entity.market.opportunity` — 市场机会/缺口分析（gap + 微改造提案 + 机会分，委托 calc.market.opportunity） — lazy 按需填充 + TTL 回填（calc.market.opportunity） 必填: `term` 依赖: `entity.market.stats`
- `entity.market.primary_pricing_dimension` — Prepare Product prices and Keyword clusters before choosing a price dimension — Entity prepares required evidence; task result is not cached 必填: `term`, `keywords`
- `entity.market.product_refs` — Fetch the market sample and save only Product references on this Market — lazy 按需填充 + TTL 回填（/competing-lookup） 必填: `term`
- `entity.market.products` — Return the legacy competitor rows projected from locally stored Products — lazy 按需填充 + TTL 回填（entity.product） 必填: `term` 依赖: `entity.market.product_refs`
- `entity.market.profile` — 8 维市场画像（综合评分，委托 calc.market.calculate_profile） — lazy 按需填充 + TTL 回填（calc.market.profile） 必填: `term` 依赖: `entity.market.stats`
- `entity.market.proposals` — Prepare VOC, gaps, and strengths for one sample before proposing changes — Entity prepares required evidence; task result is not cached 必填: `term`
- `entity.market.stats` — 计算市场画像统计（价格带/评分/上架时间/垄断度/卖家结构） — lazy 按需填充 + TTL 回填（calc.market.stats） 必填: `term` 依赖: `entity.market.products`
- `entity.market.success_factors` — Fetch and verify at least three reviewed Products, then compare strengths — Entity prepares required evidence; task result is not cached 必填: `term`
- `entity.market.summary` — 按解决方案分类竞品样本，概述人群、场景并保留 ASIN — lazy 按需填充 + TTL 回填（analysis.market.classify） 必填: `term` 依赖: `entity.market.products`
- `entity.market.tacos` — 关键词 TACOS 估算及 3/6/12 月利润分组（不含采购成本，不是净利润） — Entity prepares required evidence; task result is not cached 必填: `term`
- `entity.market.timing` — Use real dated trends and explicit launch context; never infer from a word alone — Entity prepares required evidence; task result is not cached 必填: `term`, `current_date`, `preparation_months`
- `entity.product.classify` — Apply explicit decision dimensions to this Product's prepared facts — Entity prepares required evidence; task result is not cached 必填: `asin`, `dimensions`
- `entity.product.compare` — Compare current product facts with three to five real benchmark Products — Entity prepares required evidence; task result is not cached 必填: `asin`, `benchmark_refs`
- `entity.product.competitors` — 获取竞品列表，转为 Product 实例列表 — lazy 按需填充 + TTL 回填（/competing-lookup） 必填: `asin`
- `entity.product.copyability` — 创新可复制性评估，结果写回 self.copyability — lazy 按需填充 + TTL 回填（analysis.innovation.copyability） 必填: `asin` 依赖: `entity.product.product_details`
- `entity.product.core` — 刷新 competing-lookup 提供的 Product core 字段 — lazy 按需填充 + TTL 回填（/competing-lookup） 必填: `asin`
- `entity.product.cosmo` — Extract COSMO from Listing text and optional product/A+ image text — lazy 按需填充 + TTL 回填（analysis.cosmo.extract） 必填: `asin` 依赖: `entity.product.product_details`
- `entity.product.cosmo_classify` — Rank a Market's prepared COSMO groups for this target Product — Entity prepares required evidence; task result is not cached 必填: `asin`, `market_ref`
- `entity.product.fba_fee` — Calculate FBA fees using this Product's price, package weight and dimensions — Entity prepares required evidence; task result is not cached 必填: `asin`
- `entity.product.finance` — 计算利润（毛利率 M1/M2、采购毛利、FBA 费、资金效率 ROI） — lazy 按需填充 + TTL 回填（data.fx.rate + calc.fba.margin + calc.finance.return-on-capital） 必填: `asin` 依赖: `entity.product.core`
- `entity.product.innovation` — Compatibility projection of the canonical copyability result — lazy 按需填充 + TTL 回填（analysis.innovation.copyability） 必填: `asin` 依赖: `entity.product.copyability`
- `entity.product.keyword_gap` — Check keyword coverage in this Product's current Listing — Entity prepares required evidence; task result is not cached 必填: `asin`, `keywords`
- `entity.product.keyword_relevance` — Judge explicit keywords against this Product's prepared facts — Entity prepares required evidence; task result is not cached 必填: `asin`, `keywords`
- `entity.product.listing_allocate` — Allocate supplied candidates using this Product's current Listing — Entity prepares required evidence; task result is not cached 必填: `asin`, `missing_keywords`
- `entity.product.listing_diff` — Compare proposed text with this Product or ProductDraft's saved Listing part — Entity prepares required evidence; task result is not cached 必填: `asin`, `new_text`
- `entity.product.listing_micro_insert` — Insert planned keywords into this Product's current Listing — Entity prepares required evidence; task result is not cached 必填: `asin`, `insert_plan`
- `entity.product.listing_part_rewrite` — Rewrite one existing title or bullet; its text is read from this Product — Entity prepares required evidence; task result is not cached 必填: `asin`, `part`, `keywords`
- `entity.product.listing_rewrite` — Rewrite this Product's current title and bullets; return a separate draft — Entity prepares required evidence; task result is not cached 必填: `asin`
- `entity.product.margin` — Calculate margin from Product facts and explicit cost assumptions — Entity prepares required evidence; task result is not cached 必填: `asin`
- `entity.product.market` — 获取市场聚合视图（使用主力关键词），结果写回 self.market — lazy 按需填充 + TTL 回填（aggregate） 必填: `asin` 依赖: `entity.product.primary_keyword_ref`
- `entity.product.market_opportunity` — 从 Product 直接获取 Market Opportunity；自动级联 Market 与 Stats — lazy 按需填充 + TTL 回填（entity.market.opportunity） 必填: `asin` 依赖: `entity.product.market_stats`
- `entity.product.market_profile` — 从 Product 直接获取 Market Profile；自动级联 Market 与 Stats — lazy 按需填充 + TTL 回填（entity.market.profile） 必填: `asin` 依赖: `entity.product.market_stats`
- `entity.product.market_stats` — 从 Product 直接获取 Market Stats；缺少 market 时自动级联创建 — lazy 按需填充 + TTL 回填（entity.market.stats） 必填: `asin` 依赖: `entity.product.market`
- `entity.product.material` — Assess the product's material and development difficulty from available Listing facts — lazy 按需填充 + TTL 回填（analysis.material.assess） 必填: `asin` 依赖: `entity.product.product_details`
- `entity.product.material_eligibility` — Apply material rules to this Product's prepared material assessment — Entity prepares required evidence; task result is not cached 必填: `asin`
- `entity.product.praise` — 好评深度挖掘：从 4-5 星好评中提取用户喜爱点、惊喜点、竞品对比、价值感知 — lazy 按需填充 + TTL 回填（analysis.voc.praise） 必填: `asin` 依赖: `entity.product.reviews` → `entity.product.product_details`
- `entity.product.primary_keyword_ref` — Use the first primary keyword as the sole source of the market relation — lazy 按需填充 + TTL 回填（aggregate） 必填: `asin`
- `entity.product.primary_keywords` — 筛选主力流量词（从 reverse_keywords 中按规则提取 3-8 个） — lazy 按需填充 + TTL 回填（calc.keyword.primary） 必填: `asin` 依赖: `entity.product.reverse_keywords`
- `entity.product.product_details` — 从 product-info 拉取富文本字段（五点/描述/全量图片/变体/完整类目树等，慢端点按需） — lazy 按需填充 + TTL 回填（/product-info） 必填: `asin`
- `entity.product.return_on_capital` — Calculate capital returns with this Product's price, weight and platform fees — Entity prepares required evidence; task result is not cached 必填: `asin`, `unit_cost`
- `entity.product.reverse_keywords` — 通过 ASIN 反查该商品的流量关键词列表（流量占比/自然占比/PPC 等） — lazy 按需填充 + TTL 回填（/keyword-reverse） 必填: `asin`
- `entity.product.reviews` — 获取评论集（mode: low/mid/high 每星 20/50/100 条，仅 star_filter="all" 时生效） — lazy 按需填充 + TTL 回填（/amazon/reviews） 必填: `asin`
- `entity.product.rufus_qa` — 获取商品的 Rufus AI 问答 — lazy 按需填充 + TTL 回填（/rufus） 必填: `asin`
- `entity.product.satisfaction` — Calculate satisfaction from this Product's review summary and rating — Entity prepares required evidence; task result is not cached 必填: `asin`
- `entity.product.strengths` — 创新优势分析：从 Listing 文案中找出产品真正的创新点和竞争优势 — lazy 按需填充 + TTL 回填（analysis.voc.strength-signals） 必填: `asin` 依赖: `entity.product.product_details`
- `entity.product.traffic_dimensions` — Assign price, rating and seller bands using Product facts and a Market sample — Entity prepares required evidence; task result is not cached 必填: `asin`, `market_ref`
- `entity.product.unmet_needs` — Project unmet needs from weaknesses without another model request — lazy 按需填充 + TTL 回填（entity.product.weaknesses） 必填: `asin` 依赖: `entity.product.weaknesses`
- `entity.product.use_insights` — 消费者使用洞察：场景、人群画像、购买动机 — lazy 按需填充 + TTL 回填（analysis.voc.use-signals） 必填: `asin` 依赖: `entity.product.reviews` → `entity.product.product_details`
- `entity.product.voc` — 组装 Product 三路 VOC 字段；语义分析仍由各原子能力完成 — lazy 按需填充 + TTL 回填（aggregate） 必填: `asin` 依赖: `entity.product.reviews` → `entity.product.strengths` → `entity.product.weaknesses` → `entity.product.use_insights`
- `entity.product.weaknesses` — 差评 VOC 分析：从评论中提取痛点、未满足需求，带辩证分析上下文 — lazy 按需填充 + TTL 回填（analysis.voc.weakness-signals） 必填: `asin` 依赖: `entity.product.reviews` → `entity.product.product_details`
- `entity.product.wishlist` — 用户愿望清单：从全部评论中提取功能请求、改进建议、变体需求、配件需求 — lazy 按需填充 + TTL 回填（analysis.voc.wishlist） 必填: `asin` 依赖: `entity.product.reviews` → `entity.product.product_details`
- `entity.product_draft.classify` — Apply explicit decision dimensions to this Product's prepared facts — Entity prepares required evidence; task result is not cached 必填: `draft_id`, `dimensions`
- `entity.product_draft.compare` — Compare a user supplied concept with three to five real Products — Entity prepares required evidence; task result is not cached 必填: `draft_id`, `benchmark_refs`
- `entity.product_draft.cosmo_classify` — Rank a Market's prepared COSMO groups for this target Product — Entity prepares required evidence; task result is not cached 必填: `draft_id`, `market_ref`
- `entity.product_draft.keyword_gap` — Check keyword coverage in this Product's current Listing — Entity prepares required evidence; task result is not cached 必填: `draft_id`, `keywords`
- `entity.product_draft.keyword_relevance` — Judge explicit keywords against this Product's prepared facts — Entity prepares required evidence; task result is not cached 必填: `draft_id`, `keywords`
- `entity.product_draft.listing_allocate` — Allocate supplied candidates using this Product's current Listing — Entity prepares required evidence; task result is not cached 必填: `draft_id`, `missing_keywords`
- `entity.product_draft.listing_diff` — Compare proposed text with this Product or ProductDraft's saved Listing part — Entity prepares required evidence; task result is not cached 必填: `draft_id`, `new_text`
- `entity.product_draft.listing_micro_insert` — Insert planned keywords into this Product's current Listing — Entity prepares required evidence; task result is not cached 必填: `draft_id`, `insert_plan`
- `entity.product_draft.listing_part_rewrite` — Rewrite one existing title or bullet; its text is read from this Product — Entity prepares required evidence; task result is not cached 必填: `draft_id`, `part`, `keywords`
- `entity.product_draft.listing_rewrite` — Rewrite this Product's current title and bullets; return a separate draft — Entity prepares required evidence; task result is not cached 必填: `draft_id`
- `entity.product_draft.set_facts` — Save explicitly supplied draft facts under a local draft_id — Entity prepares required evidence; task result is not cached 必填: `draft_id`, `facts`
- `entity.review.items` — 获取评论列表（按 mode/star_filter/max_pages 筛选，含 TTL 缓存） — lazy 按需填充 + TTL 回填（/amazon/reviews） 必填: `asin`
- `entity.taobao_market.sample` — 获取淘宝第一页搜索样本并保存商品引用 — lazy 按需填充 + TTL 回填（data.taobao.search） 必填: `term`
- `entity.taobao_market.summary` — 按解决方案分类淘宝样本，概述人群、场景并保留商品 ID — lazy 按需填充 + TTL 回填（analysis.taobao.market_classify） 必填: `term` 依赖: `entity.taobao_market.sample`
- `entity.taobao_product.get` — 读取已由淘宝市场采集的商品，不请求详情接口 必填: `item_id`

## 固定流程（composite）（4 个）

- `composite.compile` — 校验并落地 PipelineSpec：写 spec.json + 生成 pipeline.py + 注册为 composite.<name> 必填: `spec`
- `composite.product-development` — 商品资料 → 评论证据 → 单品分析 → 开发建议 必填: `term` 依赖: `entity.market.product_refs` → `entity.product.product_details` → `entity.product.reviews` → `entity.product.voc` → `entity.market.proposals`
- `composite.scaffold` — 生成新 pipeline 空模板（spec.json + pipeline.py 骨架）到用户 composite 目录 必填: `name`
- `composite.validate` — 校验 PipelineSpec：结构化校验 + 能力 ID 存在性校验，返回 errors 列表 必填: `spec`

## 底层数据获取（data）（18 个）

- `ads.keyword-funnel` — SIF 关键词流量漏斗 + 广告成本（搜索量/点击/订单/CPC/CPA/ACOS） 必填: `keywords`
- `category.search` — 关键词或类目名搜索 Amazon 类目
- `category.tree` — 获取 Amazon 类目树 必填: `type_`
- `data.fx.rate` — 最新日参考汇率（含报价日期与来源，非盘中成交价）
- `data.taobao.search` — 淘宝关键词第一页搜索样本 必填: `keyword`
- `keyword.miner` — 关键词特征挖掘（搜索量/PPC/点击率/转化率/Top3 ASIN） 必填: `keyword`
- `keyword.reverse` — 通过 ASIN 反查关键词列表（流量占比/自然占比/PPC） 必填: `asin`
- `keyword.trends` — 关键词趋势时间序列 必填: `keyword`
- `market.competitors` — 竞品查询：按关键词或 ASIN 拉竞品列表（支持多 ASIN + 分页）
- `market.snapshot` — 关键词商品市场快照：返回竞品样本，聚合计算由 Entity/Calc 完成 必填: `keyword`
- `product.get` — 通过 ASIN 获取商品详情（慢端点，首次调用需等 10-30s） 必填: `asin`
- `product.nr-page` — 解析 Amazon New Releases 榜单页 必填: `url`
- `product.refinements` — 获取关键词搜索的筛选维度 必填: `keyword`
- `product.reviews` — 获取 ASIN 评论列表。支持 mode (low/mid/high 每星 20/50/100 条) 或手动 star_filter/max_pages 必填: `asin`
- `product.rufus` — 获取 ASIN 的 Rufus AI 问答 必填: `asin`
- `product.search` — Amazon 关键词搜索 必填: `keyword`
- `search.web` — 火山通用 web 搜索 必填: `query`
- `supply.search-1688` — 通过图片 URL 搜索 1688 供应商（Top50 相似度排序） 必填: `asin`, `image_url`
