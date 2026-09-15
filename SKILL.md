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

## SIF 配置

分发版的 `amz setup --web` 默认让用户填写管理员提供的 SIF Token。需要生成时，
由老板或管理员主动展开“用账号生成 Token”，在本机页面填写手机号和密码。
Token/API Key 填写停止约一秒或离开输入框后自动保存，默认服务选择后立即保存。
生成的 SIF Token 立即保存并填入，可复制分发；账号密码不保存。
页面显示“已自动保存”后即可继续使用，不要求用户点保存或等待服务退出。
保存失败时先处理页面错误；配置状态为 true 只表示有值，不能证明新输入已经保存。
同一页面复用已生成的 Token，普通查询和过期错误绝不自动登录或刷新。

Token 过期时让普通使用者联系管理员更新，不引导每位同事分别登录生成。
不要在聊天中索取账号密码或 Token，也不要替用户打开生成入口并提交登录。
生成入口是可选操作入口，不是基于身份的管理员权限系统。

页面由本分发仓库 `setup_app.py` 提供，SDK wheel 不包含此生成流程。
通过源码直接运行的基础 CLI 不提供这项分发扩展。

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
