# amz-cli V1 Agent Bundle

此目录同时是 Agent Skill 和 CLI 在线安装引导包。它不依赖源码仓库。

## 1.1.0 调用约定

原有 Analysis ID 继续使用重构后的唯一实现。Skill 优先通过 Entity 准备资料、缓存和写回；
已有完整输入时直接调用 Analysis。正式入口与兼容名称见 [调用映射](references/routes.md)。

当前分析需要可用的豆包/Ark Key。旧用户只有 DeepSeek Key 时，在本机配置页补充豆包 Key。
Listing 返回独立商品亮点；VOC 比例为 null 表示缺少星级分布，不按 0% 处理。
从 Git 仓库安装的用户通过新的稳定标签更新；只有 main 有改动而版本未变时不会自动升级。

## 安装

用户电脑不需要预装 Python。

macOS 或 Linux：

```bash
bash install.sh
```

Windows PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

两个入口会准备 `uv` 和独立 Python 3.12，再安装当前目录中的 CLI wheel。用户电脑
不需要预装 Python。安装过程需要网络，用于下载 `uv`、Python 和第三方依赖。

`uv` 把 CLI 安装到独立 tool 环境，并把 `amz` 命令放入用户可执行目录。它不会修改
系统 Python。`install.py` 是已有 Python 3.11+ 环境的备用安装入口。

## 作为 Skill 分发

把整个目录注册或复制到 Honeycomb Agent 的 Skill 目录。根目录 `SKILL.md` 是唯一入口；
`references/capabilities.md` 是能力索引；`skills/` 包含全部垂类 Skill；安装脚本负责安装 CLI。

- Codex：复制为 `~/.codex/skills/amz/`。
- Claude Code：复制为 `~/.claude/skills/amz/`。
- Windows 使用相同的用户目录结构，例如 `$HOME\.codex\skills\amz\`。

也可以直接把 zip 交给 Codex 或 Claude Code，并要求它把整个目录安装为 `amz` Skill。
首次触发时，Skill 会按操作系统选择根目录的安装脚本。

安装后，Agent 可以使用：

```bash
amz capabilities
amz capabilities --id <capability_id>
amz run <capability_id> --param key=value
amz task run <capability_id> --param key=value
amz python /tmp/amz_task.py
```

安装完成后，不需要用户输入配置命令。直接对 Codex 或 Claude Code 说：

```text
帮我配置 amz-cli
```

`amz-setup` Skill 会检查安装并打开本机安全配置页。用户在页面中填写 AMZ Token、
豆包 / 火山方舟模型密钥，以及管理员提供的 SIF Token。密钥不会经过聊天，也不会包含在发布包中。

SIF 默认填写已有 Token。“用账号生成 Token”入口默认折叠，由老板或管理员主动使用：
填写手机号和密码后生成、自动保存并填入，可复制给同事；账号密码不保存，同一页面复用生成结果。
其他配置停止输入约一秒或离开输入框后自动保存，选择项立即保存。页面显示保存结果，无需点保存。
普通查询与 Token 过期不会自动登录，过期时请联系管理员更新。

分发配置页来自发行仓库 `output/setup_app.py`，不包含在基础 SDK wheel。
安装器创建的启动器负责把 `amz setup --web/--status` 接到此页面，其他命令交给基础 CLI。
请保留解压后的发布目录，配置启动器需要其中的 `setup_app.py`。

## 完整性

- `manifest.json`：版本、平台、Python、能力数量和 wheel 列表。
- `CHECKSUMS.sha256`：发布目录内文件的 SHA-256。
- `wheels/`：只包含平台无关的 CLI wheel。第三方依赖由目标电脑下载。
