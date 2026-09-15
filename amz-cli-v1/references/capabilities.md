# amz-cli 能力全索引

> 本文件由 `scripts/gen_capabilities.py` 自动生成，勿手改。生成时间：2026-09-15 18:25 UTC，共 **116** 个能力。

每个能力一行：ID + 用途 + 必填参数 + 前置依赖（`requires`）。
索引按 Agent 路由优先级排列：先 Entity，再 Composite，最后是底层能力。
需要完整可选参数与字段说明时，跑 `amz capabilities --id <id>`。
原有能力的正式入口与兼容名称见 [调用映射](routes.md)；同一任务不要重复调用兼容入口。

## 推荐入口：实体（entity）（45 个）

- `entity.keyword.aba_series` — 获取关键词 ABA 周排名序列（需 csv_path 指向 ABA CSV 文件） — lazy 按需填充 + TTL 回填（aba_file） 必填: `term`
- `entity.keyword.cluster` — 对显式候选或已有 related_keywords 做意图聚类，当前词作为主词 — lazy 按需填充 + TTL 回填（analysis.cluster.keywords） 必填: `term`
- `entity.keyword.market` — 获取该关键词的市场分析实体 — lazy 按需填充 + TTL 回填（entity.market） 必填: `term`
- `entity.keyword.market_opportunity` — 从 Keyword 直接获取 Market Opportunity；自动级联 Market 与 Stats — lazy 按需填充 + TTL 回填（entity.market.opportunity） 必填: `term` 依赖: `entity.keyword.market_stats`
- `entity.keyword.market_profile` — 从 Keyword 直接获取 Market Profile；自动级联 Market 与 Stats — lazy 按需填充 + TTL 回填（entity.market.profile） 必填: `term` 依赖: `entity.keyword.market_stats`
- `entity.keyword.market_stats` — 从 Keyword 直接获取 Market Stats；缺少 Market 时自动级联创建 — lazy 按需填充 + TTL 回填（entity.market.stats） 必填: `term` 依赖: `entity.keyword.market`
- `entity.keyword.metrics` — 获取关键词特征（core 字段刷新） — lazy 按需填充 + TTL 回填（/keyword-miner） 必填: `term`
- `entity.keyword.products` — 获取该关键词的竞品列表 — lazy 按需填充 + TTL 回填（/competing-lookup） 必填: `term`
- `entity.keyword.score` — 针对产品事实和显式候选集合评分；未传集合时使用已有 related_keywords — lazy 按需填充 + TTL 回填（analysis.keyword.score） 必填: `term`
- `entity.keyword.trends` — 获取关键词搜索量趋势时间序列（写入 self.trends） — lazy 按需填充 + TTL 回填（/seller-sprite/trends） 必填: `term`
- `entity.market.cosmo` — Aggregate verified Product COSMO results with explicit partial-failure coverage — lazy 按需填充 + TTL 回填（analysis.market.cosmo） 必填: `term` 依赖: `entity.market.product_refs`
- `entity.market.opportunity` — 市场机会/缺口分析（gap + 微改造提案 + 机会分，委托 calc.market.opportunity） — lazy 按需填充 + TTL 回填（calc.market.opportunity） 必填: `term` 依赖: `entity.market.stats`
- `entity.market.product_refs` — Fetch the market sample and save only Product references on this Market — lazy 按需填充 + TTL 回填（/competing-lookup） 必填: `term`
- `entity.market.products` — Return the legacy competitor rows projected from locally stored Products — lazy 按需填充 + TTL 回填（entity.product） 必填: `term` 依赖: `entity.market.product_refs`
- `entity.market.profile` — 8 维市场画像（综合评分，委托 calc.market.calculate_profile） — lazy 按需填充 + TTL 回填（calc.market.profile） 必填: `term` 依赖: `entity.market.stats`
- `entity.market.stats` — 计算市场画像统计（价格带/评分/上架时间/垄断度/卖家结构） — lazy 按需填充 + TTL 回填（calc.market.stats） 必填: `term` 依赖: `entity.market.products`
- `entity.market.summary` — 按解决方案分类竞品样本，概述人群、场景并保留 ASIN — lazy 按需填充 + TTL 回填（analysis.market.classify） 必填: `term` 依赖: `entity.market.products`
- `entity.product.competitors` — 获取竞品列表，转为 Product 实例列表 — lazy 按需填充 + TTL 回填（/competing-lookup） 必填: `asin`
- `entity.product.copyability` — 创新可复制性评估，结果写回 self.copyability — lazy 按需填充 + TTL 回填（analysis.innovation.copyability） 必填: `asin` 依赖: `entity.product.product_details`
- `entity.product.core` — 刷新 competing-lookup 提供的 Product core 字段 — lazy 按需填充 + TTL 回填（/competing-lookup） 必填: `asin`
- `entity.product.cosmo` — Extract COSMO from Listing text and optional product/A+ image text — lazy 按需填充 + TTL 回填（analysis.cosmo.extract） 必填: `asin` 依赖: `entity.product.product_details`
- `entity.product.finance` — 计算利润（毛利率 M1/M2、采购毛利、FBA 费、资金效率 ROI） — lazy 按需填充 + TTL 回填（data.fx.rate + calc.fba.margin + calc.finance.return-on-capital） 必填: `asin` 依赖: `entity.product.core`
- `entity.product.innovation` — Compatibility projection of the canonical copyability result — lazy 按需填充 + TTL 回填（analysis.innovation.copyability） 必填: `asin` 依赖: `entity.product.copyability`
- `entity.product.market` — 获取市场聚合视图（使用主力关键词），结果写回 self.market — lazy 按需填充 + TTL 回填（aggregate） 必填: `asin` 依赖: `entity.product.primary_keyword_ref`
- `entity.product.market_opportunity` — 从 Product 直接获取 Market Opportunity；自动级联 Market 与 Stats — lazy 按需填充 + TTL 回填（entity.market.opportunity） 必填: `asin` 依赖: `entity.product.market_stats`
- `entity.product.market_profile` — 从 Product 直接获取 Market Profile；自动级联 Market 与 Stats — lazy 按需填充 + TTL 回填（entity.market.profile） 必填: `asin` 依赖: `entity.product.market_stats`
- `entity.product.market_stats` — 从 Product 直接获取 Market Stats；缺少 market 时自动级联创建 — lazy 按需填充 + TTL 回填（entity.market.stats） 必填: `asin` 依赖: `entity.product.market`
- `entity.product.material` — Assess the product's material and development difficulty from available Listing facts — lazy 按需填充 + TTL 回填（analysis.material.assess） 必填: `asin` 依赖: `entity.product.product_details`
- `entity.product.praise` — 好评深度挖掘：从 4-5 星好评中提取用户喜爱点、惊喜点、竞品对比、价值感知 — lazy 按需填充 + TTL 回填（analysis.voc.praise） 必填: `asin` 依赖: `entity.product.reviews` → `entity.product.product_details`
- `entity.product.primary_keyword_ref` — Use the first primary keyword as the sole source of the market relation — lazy 按需填充 + TTL 回填（aggregate） 必填: `asin`
- `entity.product.primary_keywords` — 筛选主力流量词（从 reverse_keywords 中按规则提取 3-8 个） — lazy 按需填充 + TTL 回填（calc.keyword.primary） 必填: `asin` 依赖: `entity.product.reverse_keywords`
- `entity.product.product_details` — 从 product-info 拉取富文本字段（五点/描述/全量图片/变体/完整类目树等，慢端点按需） — lazy 按需填充 + TTL 回填（/product-info） 必填: `asin`
- `entity.product.reverse_keywords` — 通过 ASIN 反查该商品的流量关键词列表（流量占比/自然占比/PPC 等） — lazy 按需填充 + TTL 回填（/keyword-reverse） 必填: `asin`
- `entity.product.reviews` — 获取评论集（mode: low/mid/high 每星 20/50/100 条，仅 star_filter="all" 时生效） — lazy 按需填充 + TTL 回填（/amazon/reviews） 必填: `asin`
- `entity.product.rufus_qa` — 获取商品的 Rufus AI 问答 — lazy 按需填充 + TTL 回填（/rufus） 必填: `asin`
- `entity.product.strengths` — 创新优势分析：从 Listing 文案中找出产品真正的创新点和竞争优势 — lazy 按需填充 + TTL 回填（analysis.voc.strength-signals） 必填: `asin` 依赖: `entity.product.product_details`
- `entity.product.unmet_needs` — Project unmet needs from weaknesses without another model request — lazy 按需填充 + TTL 回填（entity.product.weaknesses） 必填: `asin` 依赖: `entity.product.weaknesses`
- `entity.product.use_insights` — 消费者使用洞察：场景、人群画像、购买动机 — lazy 按需填充 + TTL 回填（analysis.voc.use-signals） 必填: `asin` 依赖: `entity.product.reviews` → `entity.product.product_details`
- `entity.product.voc` — 组装 Product 三路 VOC 字段；语义分析仍由各原子能力完成 — lazy 按需填充 + TTL 回填（aggregate） 必填: `asin` 依赖: `entity.product.strengths` → `entity.product.weaknesses` → `entity.product.use_insights`
- `entity.product.weaknesses` — 差评 VOC 分析：从评论中提取痛点、未满足需求，带辩证分析上下文 — lazy 按需填充 + TTL 回填（analysis.voc.weakness-signals） 必填: `asin` 依赖: `entity.product.reviews` → `entity.product.product_details`
- `entity.product.wishlist` — 用户愿望清单：从全部评论中提取功能请求、改进建议、变体需求、配件需求 — lazy 按需填充 + TTL 回填（analysis.voc.wishlist） 必填: `asin` 依赖: `entity.product.reviews` → `entity.product.product_details`
- `entity.review.items` — 获取评论列表（按 mode/star_filter/max_pages 筛选，含 TTL 缓存） — lazy 按需填充 + TTL 回填（/amazon/reviews） 必填: `asin`
- `entity.taobao_market.sample` — 获取淘宝第一页搜索样本并保存商品引用 — lazy 按需填充 + TTL 回填（data.taobao.search） 必填: `term`
- `entity.taobao_market.summary` — 按解决方案分类淘宝样本，概述人群、场景并保留商品 ID — lazy 按需填充 + TTL 回填（analysis.taobao.market_classify） 必填: `term` 依赖: `entity.taobao_market.sample`
- `entity.taobao_product.get` — 读取已由淘宝市场采集的商品，不请求详情接口 必填: `item_id`

## 固定流程（composite）（3 个）

- `composite.compile` — 校验并落地 PipelineSpec：写 spec.json + 生成 pipeline.py + 注册为 composite.<name> 必填: `spec`
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
- `market.snapshot` — 市场快照（上游 market-research 禁用，默认返回 competitors 原始数据，聚合计算由 entities/calc 层负责） 必填: `keyword`
- `product.get` — 通过 ASIN 获取商品详情（慢端点，首次调用需等 10-30s） 必填: `asin`
- `product.nr-page` — 解析 Amazon New Releases 榜单页 必填: `url`
- `product.refinements` — 获取关键词搜索的筛选维度 必填: `keyword`
- `product.reviews` — 获取 ASIN 评论列表。支持 mode (low/mid/high 每星 20/50/100 条) 或手动 star_filter/max_pages 必填: `asin`
- `product.rufus` — 获取 ASIN 的 Rufus AI 问答 必填: `asin`
- `product.search` — Amazon 关键词搜索 必填: `keyword`
- `search.web` — 火山通用 web 搜索 必填: `query`
- `supply.search-1688` — 通过图片 URL 搜索 1688 供应商（Top50 相似度排序） 必填: `asin`, `image_url`

## 底层确定性计算（calc）（14 个）

- `calc.cosmo.merge` — 跨 ASIN COSMO 结果确定性合并 依赖: `analysis.cosmo.extract`
- `calc.demand.score` — 基于已获取趋势与市场数据计算需求分 依赖: `keyword.trends`
- `calc.fba.fee` — US FBA 2026 配送费查表（4 size tier + 燃油附加费） 必填: `weight_grams`, `length_cm`, `width_cm`, `height_cm`, `selling_price`
- `calc.fba.margin` — 毛利率计算（佣金 + FBA + 头程 + 采购，含 M1/M2 分层利润） 必填: `selling_price`
- `calc.finance.return-on-capital` — 资金效率计算（4 渠道物流成本 + ROI + 日回报率） 必填: `selling_price`, `unit_cost`
- `calc.keyword.gap` — Listing 的 S/A 关键词覆盖检查（确定性） 依赖: `product.get`
- `calc.keyword.primary` — 从标准化反查关键词中筛选 3-8 个主力流量词
- `calc.listing.word-diff` — 按词和空白计算 Listing LCS 差异 必填: `old_text`, `new_text`
- `calc.market.opportunity` — 根据市场统计执行确定性机会评分 必填: `stats`
- `calc.market.profile` — 把市场统计重组为稳定的 8 维画像 必填: `stats`
- `calc.market.stats` — 从标准化竞品列表计算价格、评分、评论、垄断度与卖家统计
- `calc.material.eligibility` — 按材质与可开发性结果执行门槛判定 依赖: `analysis.material.assess`
- `calc.traffic.code-dimensions` — 价格带、评分带和品牌来源确定性打标 依赖: `market.competitors`
- `calc.voc.satisfaction` — 根据全量星级分布计算产品满意度上下文

## 底层原子推理（analysis，LLM）（36 个）

- `analysis.asin.classify` — 按已发现维度为单个 ASIN 打标 依赖: `analysis.asin.discover-dimensions` → `market.competitors`
- `analysis.asin.discover-dimensions` — 发现与主定价维度正交的 2-4 个购买决策维度 依赖: `analysis.asin.primary-pricing-dimension` → `product.refinements` → `market.competitors`
- `analysis.asin.primary-pricing-dimension` — 选择解释市场价格分层的单一主规格维度 依赖: `analysis.cluster.keywords` → `product.refinements` → `market.competitors`
- `analysis.cluster.keywords` — 关键词意图聚类（两阶段，完整性校验） 依赖: `keyword.miner`
- `analysis.cosmo.aggregate` — 跨 ASIN COSMO 同义聚合（分批、跨批合并、漏词补全） 依赖: `analysis.cosmo.extract`
- `analysis.cosmo.classify` — COSMO 词组规则 30% + LLM 70% 分类与埋词位置建议 依赖: `analysis.cosmo.aggregate` → `product.get`
- `analysis.cosmo.extract` — COSMO 语义提取（Listing + 商品图/A+ 文字，5 域 19 字段及文字来源） 必填: `product_info`
- `analysis.cosmo.merge` — 兼容入口：确定性实现位于 calc.cosmo.merge 依赖: `analysis.cosmo.extract`
- `analysis.demand.assess` — 基于真实 Google/Amazon 趋势输入的确定性需求评估兼容入口 依赖: `keyword.trends`
- `analysis.innovation.compare` — 新品与 3-5 个畅销基准品的多模态差分创新评估 依赖: `product.get`
- `analysis.innovation.copyability` — 多模态创新可复制性评估（专利/供应链/技术/品牌） 依赖: `product.get`
- `analysis.keyword.gap` — 兼容入口：确定性实现位于 calc.keyword.gap 依赖: `product.get`
- `analysis.keyword.relevance` — LLM 语义相关性判断（基于搜索意图匹配） 依赖: `product.get`
- `analysis.keyword.score` — A10 四维混合评分（候选集合内百分位 + LLM 语义乘数） 依赖: `product.get`
- `analysis.listing.allocate` — 关键词位置分配（LLM 语义分配，Title + BP1-5） 依赖: `analysis.keyword.gap` → `product.get`
- `analysis.listing.micro-insert` — 在文本中自然插入关键词（微插入，最小改动） 依赖: `product.get`
- `analysis.listing.part-rewrite` — Listing 局部改写（仅改写 Title 或某一条 BP，最小改动） 依赖: `product.get`
- `analysis.listing.rewrite` — Listing 全量改写（基于关键词分层策略） 依赖: `product.get`
- `analysis.market.classify` — 按解决方案分类亚马逊商品，概述人群和场景，并保留 ASIN 与标题证据 必填: `term`, `products`
- `analysis.market.cosmo` — Aggregate Product COSMO into market synonym groups and verified sample coverage 必填: `products` 依赖: `analysis.cosmo.extract`
- `analysis.market.gap` — 市场缺口分析（兼容旧 ID） 依赖: `analysis.voc.weaknesses` → `analysis.voc.use-insights`
- `analysis.market.gap-analysis` — 市场缺口分析（规范 ID） 依赖: `analysis.voc.weaknesses` → `analysis.voc.use-insights`
- `analysis.market.proposals` — 微改造提案（兼容旧 ID） 依赖: `analysis.market.success-factors` → `analysis.market.gap-analysis`
- `analysis.market.renovation-proposal` — 微改造提案（规范 ID） 依赖: `analysis.market.success-factors` → `analysis.market.gap-analysis`
- `analysis.market.success-factors` — 提炼市场领先产品的成功因子 依赖: `analysis.voc.strengths`
- `analysis.market.timing` — 按参考日期与准备月数评估市场进入时机，默认准备3个月 依赖: `keyword.trends` → `product.get`
- `analysis.material.assess` — 新品材质与低成本可开发性多模态分析 依赖: `product.get`
- `analysis.taobao.market_classify` — 按解决方案分类淘宝商品，概述人群和场景，并保留商品 ID 与标题证据 必填: `term`, `products`
- `analysis.voc.praise` — 从好评中挖掘用户喜爱点、惊喜点、竞品对比、价值感知 依赖: `product.get` → `product.reviews`
- `analysis.voc.strength-signals` — 从严格 Listing 快照提取产品创新优势 必填: `product_info` 依赖: `product.get`
- `analysis.voc.strengths` — 产品创新优势兼容入口；新链路使用 strength-signals 依赖: `product.get` → `product.reviews`
- `analysis.voc.use-insights` — 产品使用洞察兼容入口；新链路使用 use-signals 依赖: `product.get` → `product.reviews`
- `analysis.voc.use-signals` — 从严格评论快照提取使用场景、用户画像和购买动机 必填: `product_info`, `reviews` 依赖: `product.get` → `product.reviews`
- `analysis.voc.weakness-signals` — 从已抽样评论中提取痛点和未满足需求 必填: `product_info`, `reviews`, `satisfaction` 依赖: `product.get` → `product.reviews` → `calc.voc.satisfaction`
- `analysis.voc.weaknesses` — 差评 VOC 兼容入口；新链路使用 Calc + weakness-signals 依赖: `product.get` → `product.reviews`
- `analysis.voc.wishlist` — 从评论中提取用户愿望清单：功能请求、改进建议、变体需求、配件需求 依赖: `product.get` → `product.reviews`
