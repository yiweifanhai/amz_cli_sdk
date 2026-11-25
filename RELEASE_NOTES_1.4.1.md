# amz-cli 1.4.1

## 修复：Listing 改写助手在安装版中无法运行

1.4.0 安装包没有带上 Skill 说明文件，本地工作台的“Listing 改写助手”和“产品改进助手”在安装版中不显示；直接运行会报 `FileNotFoundError`，不会发出任何改写调用。源码运行不受影响。

- 安装包现在内置全部 Skill 说明；构建时逐字节核对，缺失或与源码不一致直接构建失败。
- 规划模型在报告里直接输出换行，曾导致“Model response is not a JSON object or array”，已完成的改写结果随之丢失。现在可以正确解析；动作格式出错时带错误说明重试一次，仍受规划 token 上限约束。
- 本次提供草稿事实（`draft_facts`）时，必须先保存，再改写，避免沿用同一 `draft_id` 下的旧资料。
- 只分配关键词（`listing_allocate`）的任务现在可以正常交付。

命令行直接调用 `entity.product.listing_rewrite` 等 Entity 能力在 1.4.0 中正常，本次不变。

如果你的 Agent 使用的是自行复制的 1.1.x Skill 文件，其中的 `analysis.listing.*` 入口自 1.2.0 起已停用，请用本版本 `skills/amz-listing-rewrite/SKILL.md` 替换。

## 修复：`entity.market.solution_outlook` 证据校验

- 疑似换链的商品不再与已验证商品一起被引用，也不进入代表样本。
- 程序降级判定后，摘要和理由会加上【程序修正】标记，不再与等级矛盾。
- 修正恰好 3 倍时的误判；模型给出低置信度时补充商品线说明。

## 边界

- 同一任务同时要求“分配关键词”和“改写”时，助手可能只交付分配结果；需要改写时请明确要求全量改写。
- solution_outlook 的商品分组仍由模型按标题判断，个别商品可能被分错组。

已有安装会在 24 小时内的下一次 `amz` 命令时自动更新；立即升级可运行 `amz-update --force`。
