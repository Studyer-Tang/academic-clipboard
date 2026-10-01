# Academic Clipboard

轻量、本地优先的科研剪贴板：找回复制过的文本和截图，整理出处、页码与批注，再复制到论文、Word、Excel 或笔记中。无需账号、网络服务或 AI 模型。

An offline research clipboard for Windows and macOS. Search snippets, keep sources, clean copied PDF prose and reuse text/images. Python + Tk + SQLite; no browser runtime or telemetry.

## 下载使用

从 [Releases](https://github.com/Studyer-Tang/academic-clipboard/releases) 选择 **0.5 系列预览版**：

| 电脑 | 下载 | 使用 |
| --- | --- | --- |
| Windows 10/11 x64 | `Windows-x64.zip` | 完整解压，运行文件夹内 `AcademicClipboard.exe`，不要只移动 EXE |
| Apple Silicon Mac（M 系列） | `macOS-arm64.dmg` | 打开 DMG，把应用拖入 Applications 后启动 |
| Intel Mac | `macOS-x64.dmg` | 同上，选择 Intel 对应版本 |

包内已包含 Python 和依赖，无需安装开发环境。每个下载附带 SHA-256 文件。**当前没有 Apple Developer ID 公证或 Windows 发布者签名**，系统可能提示未知开发者；按照系统的安全设置提示核实来源后允许打开，不需要关闭系统安全保护。Mac 构建在 macOS 15 上验收，更早系统尚未验证。Linux 提供源码/CLI，未承诺同等桌面能力。

默认在屏幕右侧打开紧凑窗口。点击 `Ⅱ / ▶` 暂停或恢复监听；`↗` 展开详情；`?` 查看快捷键。关闭窗口后保留在 Windows 托盘或 Mac 菜单栏 **AC** 菜单，通过菜单可显示、暂停、退出。若托盘不可用，关闭窗口会直接退出，避免留下无法访问的后台进程。

## 常用科研工作流

- **PDF → 干净文本**：选中片段 →「转换」→「合并 PDF 断行」。保留空行分段；中英文均可。另提供需核对的连字符合并，不修改保存的原文，不自动清洗代码和表格。
- **摘录 → 带出处引用**：按 `E` 填写来源、页码/章节、项目、标签及批注；「带出处复制」一并带走原文与定位。出处由用户填写，不自动猜测当前论文。
- **BibTeX → Zotero / 写作**：保留原始 BibTeX，支持 `.bib` 导出供 Zotero 导入；GB/T 7714、APA 仅生成待校对草稿，不冒充完整引文排版引擎。
- **表格 → Excel / Word / LaTeX**：制表符、Markdown 表格互转，提供 LaTeX `tabular`。制表符结果可粘贴到 Excel；Word 中可用“文本转换成表格”。
- **公式、DOI、代码**：切换行内/独立 LaTeX，复制 DOI 链接、Markdown 引文或代码块。
- **截图复用**：Windows 截图，或 Mac `Control+Shift+Command+4` 截图到剪贴板，自动保存 PNG，可预览、搜索标签并复制回其他软件。普通文件复制不会被导入为截图。
- **查找与整理**：全文和研究信息检索、类型筛选、置顶、批量文本复制、Markdown/JSON 导出。界面显示最近 500 条匹配预览，搜索覆盖完整历史。

「带出处复制」和其他文本结果可正常粘贴到 Word；本项目不提供 Word 插件或自动生成 `.docx`。

## 快捷键

| 操作 | Windows | macOS |
| --- | --- | --- |
| 全局唤出 | `Ctrl+Alt+V` | `Control+Option+V` |
| 搜索 | `Ctrl+F` | `Command+F` |
| 复制原文 / 格式化内容 | `Ctrl+Enter` / `Ctrl+Shift+Enter` | `Command+Enter` / `Command+Shift+Enter` |
| 列表全选 | `Ctrl+A` | `Command+A` |
| 上下选择、复制 | 方向键、`Enter` | 相同 |
| 最近第 1–9 项 / 编辑 | `1–9` / `E` | 相同 |
| 清空搜索，再次隐藏 / 帮助 | `Esc` / `F1` | 相同 |

全局组合可在设置中修改，Mac 支持 `Cmd`、`Option` 名称；字母键按 ANSI 物理位置注册。系统占用的组合会显示注册失败，可换一个组合。Mac 不需要为此授予辅助功能或键盘监听权限。复制后切换到目标软件自行粘贴，程序不会模拟按键注入。

## 体积、性能与隐私

- 只在系统剪贴板变化后读取内容；暂停时不读取文本/图片。同一截图不会每 650 毫秒重新压缩。
- 列表只读取 240 字符预览，选中后读取全文。500 条长文本的本地测试中，查询峰值 Python 分配从 **95.85 MiB 降至 0.49 MiB**；这不是应用总 RAM。[测量方法和限制](docs/research-and-validation.md)。
- 默认保留 90 天、最多 2000 条未置顶记录、256 MiB 未置顶正文/图片。设置可调整；置顶条目不自动删除。SQLite 空闲页可复用，数据库文件和置顶内容不受该载荷上限严格限制。
- 单张图片最大 1600 万像素、PNG 最大 32 MiB；超过限制会提示跳过。超大截图仍可能短暂影响响应。
- macOS 尊重保密/临时剪贴板标记；各平台默认过滤常见密钥、Token 和验证码模式。过滤不能识别所有秘密，截图也不会做敏感内容 OCR。
- 数据是**本机明文**，无上传、遥测、联网查 DOI。需要保密时请暂停监听。

| 系统 | 数据目录 |
| --- | --- |
| Windows | `%LOCALAPPDATA%\AcademicClipboard` |
| macOS | `~/Library/Application Support/AcademicClipboard` |
| Linux | `$XDG_DATA_HOME/academic-clipboard`，默认 `~/.local/share/academic-clipboard` |

目录包含 `clipboard.db`、`images/` 和设置。退出程序后复制整个目录可备份；JSON/Markdown 导出包含图片路径，不打包图片本体。`ACADEMIC_CLIPBOARD_HOME` 可指定独立数据目录。旧版数据库首次启动自动迁移，升级前建议备份。

## 源码与开发

使用 Python 3.10+，须包含 Tkinter（python.org 标准安装版包含；Linux 可安装系统 `python3-tk`）。

```sh
git clone https://github.com/Studyer-Tang/academic-clipboard.git
cd academic-clipboard
python -m venv .venv
# Mac/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,packaging]"
python -m academic_clipboard
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
python scripts/benchmark.py
python scripts/build_release.py
```

`Desktop builds` 工作流为 Windows x64、Mac arm64/x64 分别构建，运行单元测试并启动实际打包程序后生成 ZIP/DMG。PR 上传测试包；`v*` 标签仅在全部构建成功后发布预览版。

```sh
academic-clipboard run --paused      # 启动时不读取剪贴板内容
academic-clipboard launch            # 后台托盘/菜单栏启动
academic-clipboard startup enable    # 当前用户下次登录启动（Windows/macOS）
academic-clipboard startup disable
academic-clipboard startup status
academic-clipboard list --limit 20
academic-clipboard search "causal inference"
academic-clipboard export notes.md
academic-clipboard export history.json
academic-clipboard export references.bib
academic-clipboard stats
academic-clipboard clear --yes       # 删除未置顶历史
```

CLI 数据命令可在子命令前加 `--database PATH`。桌面程序使用数据目录中的数据库。Mac 开机启动使用当前用户 LaunchAgent，Windows 使用当前用户 Run 键；不需要管理员权限，移动安装位置后需重新启用。

[架构](docs/architecture.md) · [需求调研与验证](docs/research-and-validation.md) · [安全边界](SECURITY.md) · [MIT License](LICENSE)
