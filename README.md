# amz-cli Agent 发行仓库

把本仓库链接发给 Codex、Claude Code 或其他可运行终端命令的 Agent，它就能安装
amz-cli。安装后，`amz` 在使用前按间隔检查稳定版本，并自动更新。已有 API Key、Token、
缓存和任务数据不会被覆盖。

## 发给 Agent 的一句话

```text
请把这个仓库克隆到持久的 Skill 目录，完整读取 README.md 和 SKILL.md，安装 amz-cli，
检查配置状态；如果尚未配置，打开本机配置页并等待我保存。最后运行 amz version --json
与 amz doctor。不要读取或回显我本机已有的任何 Key。
```

不要只下载 zip 后安装。自动更新需要保留 Git clone。

## 首次发布到 GitHub

本地仓库已经包含 `main` 首次提交和 `v1.0.0` 标签。创建空的 GitHub 仓库后运行：

```bash
cd /Users/shuxin/kjprojects/amz-cli/output
git remote add origin <GITHUB_REPO_URL>
git push -u origin main
git push origin v1.0.0
```

不要在 GitHub 建仓时自动添加 README、LICENSE 或 `.gitignore`，否则会产生两份不同的
首次提交。更新器会读取每个用户 clone 中的 `origin`，仓库名称不需要写死在安装器里。

## 安装

Codex：

```bash
git clone <GITHUB_REPO_URL> ~/.codex/skills/amz
bash ~/.codex/skills/amz/install.sh --setup
```

Claude Code：

```bash
git clone <GITHUB_REPO_URL> ~/.claude/skills/amz
bash ~/.claude/skills/amz/install.sh --setup
```

其他 Agent 或只安装 CLI：

```bash
git clone <GITHUB_REPO_URL> ~/.local/share/amz-cli/repo
bash ~/.local/share/amz-cli/repo/install.sh --setup
```

Windows PowerShell 把最后一条命令换成：

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Setup
```

安装器会准备 `uv` 和独立 Python 3.12，再安装仓库中的 wheel。它不修改系统 Python。
`--setup` / `-Setup` 会在安装后打开只监听 `127.0.0.1` 的配置页。Key 直接保存到本机，
不会经过聊天。已有配置留空即可保留。

## 自动更新

安装器把公开命令和真实 CLI 分开：

```text
~/.local/bin/amz                 启动器：先按间隔检查更新
~/.local/bin/amz-update          手动更新命令
~/.local/share/amz-cli/tools/    隔离的 CLI 环境
<Git clone>/                     wheel、Skill 和更新程序
```

默认每 24 小时最多联网检查一次。更新器只接受严格的稳定标签 `vX.Y.Z`，在临时 Git
worktree 中校验 manifest、全部 SHA-256 和 wheel 后再安装。新 CLI 验证成功后才切换
Skill 仓库。失败时保留旧版本，随后继续执行原命令。

```bash
amz-update --force                         # 立即检查
AMZ_CLI_UPDATE_INTERVAL_HOURS=168 amz ...  # 每 7 天检查
AMZ_CLI_AUTO_UPDATE=0 amz ...              # 关闭自动更新
AMZ_CLI_SKIP_UPDATE=1 amz ...              # 本次跳过
```

## Key 为什么不需要重新配置

程序和配置在不同目录。安装器和更新器从不调用 `amz setup`，也不读写以下文件：

- `~/.amz/config.yaml`
- `~/.amz/.env`
- `~/.sif_token`
- `~/.cache/amz-cli/`
- `~/.amz/amz-cli.db`

升级只替换 `~/.local/share/amz-cli/tools/` 中的隔离环境。需要首次配置或主动换 Key 时，
使用 `amz setup --web`。不要把 Key 写在聊天或命令行参数中。

## 仓库内容

- `SKILL.md`：Agent 安装、更新和任务入口。
- `manager.py`：统一安装、校验、更新和回滚逻辑，只使用 Python 标准库。
- `install.sh` / `install.ps1`：无 Python 环境的启动脚本。
- `amz-cli-v1/`：当前 major 版本的 wheel、完整 Skill、能力索引和校验文件。

## 发布新版本

1. 在源码仓库同时更新 `pyproject.toml` 和 `amz.__version__`。
2. 运行源码仓库的 `scripts/build_release.py`，让它刷新本仓库的 `amz-cli-v1/`。
3. 在本仓库运行 `python3 manager.py verify` 和测试。
4. 提交变更，创建与 manifest 一致的标签，例如 `v1.0.1`。
5. 推送提交和标签。GitHub Actions 会验证并创建 Release 附件。

标签、`manifest.json`、wheel 文件名和 CLI 的实际版本必须完全一致。
