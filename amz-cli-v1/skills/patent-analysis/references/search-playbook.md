# 专利检索与状态核对手册

## 官方入口

| 来源 | URL | 用途 |
|---|---|---|
| USPTO Patent Public Search | https://ppubs.uspto.gov/basic/ | 按编号、关键词、申请人和分类搜索授权专利与公开申请 |
| USPTO 在线专利工具 | https://www.uspto.gov/patents/basics/online-patent-tools | Patent Public Search、Patent Center 等入口 |
| USPTO Patent File Wrapper | https://data.uspto.gov/patent-file-wrapper/search | 申请数据、文档与审查历史 |
| USPTO 维护专利 | https://www.uspto.gov/patents/maintain | 维护费、失效信息和期限计算工具 |
| USPTO 外观期限 | https://www.uspto.gov/web/offices/pac/mpep/s1505.html | 美国外观专利 14/15 年规则 |
| PatentsView API | https://search.patentsview.org/docs/docs/Search%20API/SearchAPIReference/ | 结构化候选搜索；当前要求 API Key |

## 搜索词拆分

为每个产品建立四组英文词：

- 品类词：普通消费者对产品的名称。
- 功能词：产品完成的动作或解决的问题。
- 结构词：连接、折叠、锁定、支撑、密封、传动等具体结构。
- 变体词：同义词、旧称、上位词和替代技术。

先用 2-3 个高辨识度结构词搜索。结果过少时逐步放宽，结果过多时加入申请人、分类或日期过滤。
保存每次查询原文和过滤条件。不要只搜 Listing 的营销词。

## 已知编号路线

1. 规范化公开号、专利号和申请号，但在报告中保留原始写法。
2. 打开文献，记录类型、授权或公开日期、申请人和当前受让人。
3. 检查连续申请、分案、再颁和相关申请，避免只看一个家庭成员。
4. 阅读独立权利要求；把目标产品特征逐项映射到权利要求限制。
5. 在 File Wrapper 或官方维护费入口核对状态，记录不能确认的因素。

## 外观路线

1. 准备正面、侧面、顶部和透视图；去除水印与无关背景，但不改变产品轮廓。
2. 用图片数据库找候选，用文字和 Locarno/USPC 分类补查。
3. 对候选逐项记录整体轮廓、比例、表面装饰、开孔、棱线、曲面和明确差异。
4. 图片相似度只用于排序。不要设置“高于某百分比即侵权”的固定阈值。
5. 回到官方文献核对所有图纸、虚线范围、权利人和状态。

## 法律状态纪律

- 授权、有效、未过期和未失效不是同一个概念。
- 实用专利期限可能受最早有效申请日、PTA、PTE、终止免责声明、再审和维护费影响。
- 外观专利申请日在 2015-05-13 当天或之后时，通常为自授权起 15 年；更早申请通常为 14 年。
- 简单期限估算只标为 `estimated`。没有官方状态证据时使用 `unknown`。
- 公开申请不是已授权专利，但可能形成未来风险；单独标记 `pending`。

## PatentsView

PatentsView PatentSearch API 当前要求请求头 `X-Api-Key`，并有限流。官方文档还说明新 Key 发放可能
暂停。只有环境已经配置 Key 时才使用它；不要把旧版“免费且无需 Key”的说明带入新 Skill。

## 停止条件

- 找到高相关有效候选：停止无边界扩展搜索，转入权利要求、图纸和状态核对。
- 连续多组同义词和分类搜索都没有新候选：记录覆盖范围与盲区后停止。
- 数据源不可用：输出 `UNKNOWN` 和未完成项，不以“零结果”降为 `LOW`。
