# amz-cli 1.2.0

配置一次个人 SellerSprite MCP Token，继续使用原有业务命令，由服务端透传取数。平台 API Key 仍需保留；个人 Token 可选。

- 配置页支持保存、替换和清除 Token，也支持 Token 文件和环境变量。
- 兼容卖家精灵五类接口的新旧响应，修复销量、评论数、BSR、关键词匹配和缓存。缺失精准 PPC 返回空值，词组 PPC 单独保留。
- 个人 Token 请求失败不自动换平台凭据，不自动重试；共享缓存命中不消耗个人 MCP 额度。
- 包含此前已完成的 Entity/Calc/Analysis 业务入口整理、市场 TACOS 分析及共享能力契约更新。

升级后运行 `amz setup --web` 配置可选 Token；原有命令与服务认证继续使用。已有安装可通过 `amz-update --force` 检查新版本。

开发者注意：Calc/Analysis 只供内部实现调用，公开业务使用 Entity；已移除旧 Python 模块路径，直接导入内部模块的调用方需调整。

验证范围：CLI 单元、配置页、前端、离线 MCP 请求链路与发行包验证。真实个人 Token、生产部署和 Listing 免扣 Credit 策略尚未线上验收。Spider 不负责计费，个人 Token 免费策略需要 Listing 计费层配合。本版本不承诺全量官方 MCP 工具均已开放。
