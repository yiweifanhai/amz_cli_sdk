---
name: amz
description: >
  安装、更新和使用 amz-cli。适用于 Amazon 商品、关键词和市场数据，利润率与 FBA
  费用计算，VOC 评论分析，Listing 优化，竞品与市场分析，选品、新品、需求和风险判断。
  本 Skill 从稳定 Git 标签自动更新 CLI、能力索引和垂类 Skill，并保留用户已配置的 Key。
---

# amz-cli 发行入口

## 每次任务的预检

先运行：

```bash
amz version --json
```

安装器创建的 `amz` 启动器会在到达检查间隔时自动检查 Git 稳定版本标签。默认间隔是
24 小时。没有新版本时直接运行；有新版本时先校验、安装和验证，再切换本仓库内容。
网络或更新失败不会删除当前版本，也不应阻断本次 Amazon 任务。

如果 `amz` 不存在，按当前系统运行本仓库根目录的安装器：

```bash
# macOS / Linux：安装后打开本机配置页
bash <本仓库>/install.sh --setup

# Windows PowerShell：安装后打开本机配置页
powershell -ExecutionPolicy Bypass -File <本仓库>\install.ps1 -Setup
```

必须从持久 Git clone 安装，不能安装后删除本仓库。更新器需要 Git 标签，同时要更新
CLI、能力索引和垂类 Skill。

如果 CLI 已安装，先运行 `amz setup --status --json`。只根据布尔状态判断是否已配置，
不要读取配置文件。只有缺少用户需要的 Token 或 Key 时，才运行 `amz setup --web`。

## 更新控制

```bash
amz-update --force
```

- 默认每 24 小时最多检查一次。
- `AMZ_CLI_UPDATE_INTERVAL_HOURS=168` 可改成每 7 天检查一次。
- `AMZ_CLI_AUTO_UPDATE=0` 可关闭自动更新。
- `AMZ_CLI_SKIP_UPDATE=1 amz ...` 可只跳过当前命令的检查。

## 配置保护

安装和更新只替换隔离的 CLI 环境和本 Git 仓库内容。它们不读取或修改：

- `~/.amz/config.yaml`
- `~/.amz/.env`
- `~/.sif_token`
- `~/.cache/amz-cli/`
- `~/.amz/amz-cli.db`

不要要求用户在聊天中发送 Key。只有用户明确要求新增或更换配置时，才读取
`amz-cli-v1/skills/amz-setup/SKILL.md`，并使用本机配置页。

## Amazon 任务路由

预检完成后，完整读取：

```text
amz-cli-v1/SKILL.md
```

该文件是 CLI 能力选择和垂类 Agent 路由的正式说明。能力快速索引位于：

```text
amz-cli-v1/references/capabilities.md
```
