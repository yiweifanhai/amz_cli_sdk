# amz-cli 1.4.0

## 卖家精灵：MCP 失败自动改走默认 API

配置了个人 SellerSprite MCP Token 后，竞品查询、关键词反查、关键词挖掘、趋势和类目研究请求先带 Token 走 MCP，只发一次。
MCP 失败（网络、HTTP 或业务错误）时，同一请求自动去掉 Token，改走服务端默认 API，最多重试三次。

- 回退成功时结果正常返回并缓存，`meta.hint` 标注 `sellersprite mcp failed (<code>); served by default api`。
- 两条路都失败时，错误信息同时列出 `mcp:` 与 `api:` 两段，Token 已脱敏。
- 回退使用服务端默认账号，不消耗个人额度。商品详情、评论、SIF、1688 等接口没有 MCP 通道，不受影响。

1.3.0 中配置了 Token 的用户在 MCP 出错时会直接报错（如 `HTTP 500`、`HTTP POST failed`），升级后不再需要手动清除 Token。

## 新增：创新方向证据卡 `entity.market.solution_directions`

```bash
amz run entity.market.solution_directions --param 'term=picture hanging tool'
```

- 按父体合并商品线，模型只按标题打方案标签，程序用已验证新品、亚马逊前台销量标记、新老份额变化和跟进起量给方向定 A/B/C。
- 可选 `pages`、`taobao_term`（默认不查淘宝）、`explain`（默认为 A/B 卡写解释）。没有已验证新品线的市场不出卡，也不调用模型。
- 样本缺少标题、上架日、月销和销售额或价格时返回缺项错误；旧导入残留、本次样本未观测到的字段不参与判断。

## `entity.product.novelty` 召回改进

- 新增 `terms`：每个词单独取一个市场样本，不依赖关键词反查。
- 新增方案词召回：从本品标题抽取 2–4 个词搜索同方案商品（不设销量门槛），搜索为 0 时逐个去掉开头词重试；模型预筛结果单独成组，召回“做过但没卖起来”的同方案产品。
- 老品口径改为早于本品上架 `min_lead_months`（默认 6 个月）；同方案但原理、形态或功能明显升级的记入 `upgrades`，不算已有方案。
- 输出增加匹配老品的月销、来源、查询词和匹配类型，以及 `sample.coverage` 搜索覆盖说明。

## 配置清理

- AI 分析统一只需豆包（火山方舟）Key。`amz setup` 或配置页保存时会清理已停用的 DeepSeek 等旧设置；自定义后端保持不变。
- `amz doctor` 增加本地豆包 Key 检查和残留设置提示；缺 Key 时提示运行 `amz setup`。

## 边界

- 市场样本只代表搜索前几页；方向卡阈值未经回测，A 级表示证据较硬，不代表创新程度高。
- 卖家精灵 MCP 本身的服务端故障仍在修复中，修复前带 Token 的请求会走回退。

已有安装会在 24 小时内的下一次 `amz` 命令时自动更新；立即升级可运行 `amz-update --force`。
