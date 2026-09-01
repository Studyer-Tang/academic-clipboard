# Academic Clipboard

面向学生、研究者和开发者的本地优先剪贴板历史与研究片段管理器。它会连续保存文本和截图剪贴板内容，让你选择历史记录，再粘贴到 Word、Markdown 编辑器、浏览器或代码编辑器。

A local-first clipboard history and research-snippet manager for students, researchers, and developers. Capture text and screenshots continuously, preview them locally, and copy them back when needed.

## 功能 / Features

- 文本与截图剪贴板历史、搜索、类型筛选、置顶和删除；文本支持批量复制。
- Windows 截图自动保存为本地 PNG，展开窗口可预览，并可把任一历史截图重新复制到其他软件。
- 默认以 390×380 的屏幕右侧置顶悬浮窗启动，还可继续手动缩小，阅读时不遮挡主要内容，并可一键展开完整详情。
- 高 DPI 响应式布局，在常见 Windows 缩放比例下保持操作栏可见。
- `Ctrl+Alt+V` 全局唤出，方向键选择、Enter 复制，数字 `1–9` 快速复制最近条目。
- 编辑标题、内容和标签；搜索会同时匹配标签。
- 跟随系统、浅色和深色三种主题，以及应用内设置窗口。
- 多选记录按顺序合并；原文和智能格式化结果可分别复制。
- DOI 自动识别并转换为 Markdown 链接。
- BibTeX 自动整理缩进与字段格式。
- 论文标题生成 Markdown 阅读笔记模板。
- Python、JavaScript、SQL、Shell、JSON 等代码自动保存为 fenced snippet。
- URL 自动分类为论文、文档、数据集、GitHub/GitLab 仓库或普通网页。
- 默认跳过疑似密码、Token、私钥、Authorization header 和验证码。
- SQLite 与 PNG 本地存储，无账号、无遥测、无云服务，图片不会上传。
- 中英双语界面；Windows 优先，同时保留 macOS/Linux 的 Tkinter 基础兼容性。

## 快速开始 / Quick start

需要 Python 3.10 或更新版本，并包含标准库 Tkinter/Tcl-Tk。建议 Windows 用户从 [python.org](https://www.python.org/downloads/) 安装标准版 Python。Windows PowerShell：

```powershell
git clone https://github.com/Studyer-Tang/academic-clipboard.git
cd academic-clipboard
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\academic-clipboard.exe
```

如果还没有克隆仓库，也可以在项目目录直接执行后四条命令。Linux/macOS 使用 `./.venv/bin/python` 和 `./.venv/bin/academic-clipboard`。

如果启动时提示缺少 Tkinter，Windows 请重新运行 Python 安装程序并启用 `tcl/tk and IDLE`；Ubuntu/Debian 可安装系统包 `python3-tk`。CLI 数据管理命令不依赖图形界面。

程序运行期间会监听文本和截图剪贴板。使用 `Win+Shift+S` 等工具截图后，图片会自动出现在历史中；展开窗口并选中图片即可预览。按 `Ctrl+Alt+V` 随时唤出小窗；使用方向键选择后按 Enter，或按数字 `1–9` 快速复制。复制完成后默认自动隐藏。文本可用 `Ctrl` 或 `Shift` 多选后合并复制；图片需要一次复制一张。点击标题栏的 `?` 或按 `F1` 可随时查看应用内快捷键说明。点击 **Expand / 展开** 可进入完整管理界面；再次点击 **Compact / 悬浮** 回到小窗。

关闭窗口右上角的 `×` 后，程序会缩到 Windows 右下角系统托盘并继续监听，不再退出。双击托盘图标可以恢复小窗；右键菜单可暂停监听或彻底退出。如果图标没有直接显示，请在任务栏右侧的 `^` 隐藏图标区域中查找。

### 无终端启动与开机启动 / Tray launch

日常使用不需要一直保留 PowerShell。首次安装完成后，可执行一次：

```powershell
.\.venv\Scripts\academic-clipboard.exe launch
```

命令会立即返回，程序在后台托盘运行。也可以直接双击项目根目录的 `launch-academic-clipboard.vbs`。若要登录 Windows 后自动在托盘启动：

```powershell
.\.venv\Scripts\academic-clipboard.exe startup enable
.\.venv\Scripts\academic-clipboard.exe startup status
.\.venv\Scripts\academic-clipboard.exe startup disable
```

开机启动只写入当前 Windows 用户的 `HKCU\...\Run` 项，不需要管理员权限。移动项目目录或重建 `.venv` 后，请重新执行 `startup enable` 更新路径。

## 命令行 / CLI

```powershell
academic-clipboard                 # 启动桌面界面
academic-clipboard launch          # 无终端启动到系统托盘
academic-clipboard startup enable  # 当前用户登录后自动启动
academic-clipboard list --limit 20
academic-clipboard search "causal inference"
academic-clipboard list --kind doi --json
academic-clipboard export clipboard-notes.md
academic-clipboard export clipboard-history.json
academic-clipboard stats
academic-clipboard clear --yes     # 保留置顶项
academic-clipboard clear --all --yes
```

所有子命令均可用 `--database PATH` 指定另一份 SQLite 数据库，例如：

```powershell
academic-clipboard --database .\demo.db list
```

## 快捷键 / Shortcuts

| 快捷键 | 操作 |
| --- | --- |
| `Ctrl+F` | 聚焦搜索框 |
| `Ctrl+Enter` | 复制所选原文 |
| `Ctrl+Shift+Enter` | 复制所选格式化内容 |
| `Ctrl+A`（列表聚焦时） | 选择当前列表全部项目 |
| `Ctrl+Alt+V`（全局） | 从其他程序唤出剪贴板小窗 |
| `Enter`（列表聚焦时） | 复制所选并按设置自动隐藏 |
| `1`–`9`（列表聚焦时） | 快速复制对应的最近条目 |
| `E`（列表聚焦时） | 编辑当前片段和标签 |
| `Delete` | 删除所选项 |
| `Esc` | 清空搜索；再次按下隐藏窗口 |
| `F1` | 打开应用内快捷键说明 |
| 双击列表项 | 复制该项原文 |

## 数据与隐私 / Data and privacy

默认数据库位置：

- Windows: `%LOCALAPPDATA%\AcademicClipboard\clipboard.db`
- macOS: `~/Library/Application Support/AcademicClipboard/clipboard.db`
- Linux: `$XDG_DATA_HOME/academic-clipboard/clipboard.db`

截图保存在同一数据目录下的 `images/` 文件夹中，文件名使用内容哈希生成。相同截图不会产生重复文件；删除记录、清空历史或自动清理过期记录时，对应图片文件也会一起删除。

设置环境变量 `ACADEMIC_CLIPBOARD_HOME` 可以改变数据目录。

重要：当前数据库是本机**明文 SQLite 文件**。敏感内容过滤只是降低误存风险，不能保证识别所有秘密。请不要把数据库提交到 Git，也不要在共享电脑上保存机密内容。详见 [SECURITY.md](SECURITY.md)。项目不会读取账号密码，也没有上传或遥测代码。

## 当前边界 / Current limits

- 图片剪贴板与图片回写目前以 Windows 为主要支持平台；复制的普通文件不会被当成截图保存。
- 图片记录可预览、置顶、搜索和单张复制，暂不支持图片编辑或与文本混合批量复制。
- 当前支持 Windows 系统托盘；macOS/Linux 的托盘行为取决于桌面环境。
- 全局快捷键目前仅在 Windows 提供；其他系统可通过托盘图标显示窗口。
- 标题、代码语言与 URL 类别使用本地规则推断，可在编辑窗口中人工修正标题和标签。
- 不联网查询 DOI 元数据，也不会自动访问论文网页。

## 开发 / Development

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\ruff.exe check .
```

架构说明见 [docs/architecture.md](docs/architecture.md)，贡献方式见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## Roadmap

- v0.4：可选 DOI 元数据、系统密钥保护和文件历史导入策略。
- v1.0：稳定的数据迁移、无障碍改进、签名桌面安装包。

## Windows portable build

仓库包含 `Windows portable app` GitHub Actions 工作流。手动运行该工作流或推送 `v*` 标签后，会生成无需终端的 `AcademicClipboard.exe` 构建产物。开发者也可安装 `.[packaging]` 后使用相同的 PyInstaller 参数本地构建。

## License

[MIT](LICENSE)
