# Academic Clipboard

面向学生、研究者和开发者的本地优先剪贴板历史与研究片段管理器。它会连续保存文本剪贴板内容，让你一次选择多条记录，再以原文或格式化结果粘贴到 Word、Markdown 编辑器、浏览器或代码编辑器。

A local-first clipboard history and research-snippet manager for students, researchers, and developers. Capture text continuously, select multiple entries, and copy them back as original or formatted content.

## 功能 / Features

- 多条文本剪贴板历史、搜索、类型筛选、置顶、删除和批量复制。
- 多选记录按顺序合并；原文和智能格式化结果可分别复制。
- DOI 自动识别并转换为 Markdown 链接。
- BibTeX 自动整理缩进与字段格式。
- 论文标题生成 Markdown 阅读笔记模板。
- Python、JavaScript、SQL、Shell、JSON 等代码自动保存为 fenced snippet。
- URL 自动分类为论文、文档、数据集、GitHub/GitLab 仓库或普通网页。
- 默认跳过疑似密码、Token、私钥、Authorization header 和验证码。
- SQLite 本地存储，无账号、无遥测、无云服务、无运行时第三方依赖。
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

程序运行期间会监听文本剪贴板。复制多段内容后，在列表中按 `Ctrl` 或 `Shift` 多选，点击 **Copy selected / 复制所选**，再到目标程序按 `Ctrl+V`。

## 命令行 / CLI

```powershell
academic-clipboard                 # 启动桌面界面
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
| `Delete` | 删除所选项 |
| `Esc` | 清空搜索 |
| 双击列表项 | 复制该项原文 |

## 数据与隐私 / Data and privacy

默认数据库位置：

- Windows: `%LOCALAPPDATA%\AcademicClipboard\clipboard.db`
- macOS: `~/Library/Application Support/AcademicClipboard/clipboard.db`
- Linux: `$XDG_DATA_HOME/academic-clipboard/clipboard.db`

设置环境变量 `ACADEMIC_CLIPBOARD_HOME` 可以改变数据目录。

重要：当前数据库是本机**明文 SQLite 文件**。敏感内容过滤只是降低误存风险，不能保证识别所有秘密。请不要把数据库提交到 Git，也不要在共享电脑上保存机密内容。详见 [SECURITY.md](SECURITY.md)。项目不会读取账号密码，也没有上传或遥测代码。

## 当前边界 / Current limits

- v0.1 只捕获文本，不捕获图片或文件。
- 关闭主窗口后监听即停止；暂不提供系统托盘和全局快捷键。
- 标题、代码语言与 URL 类别使用本地规则推断，可能需要人工修正。
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

- v0.2：可编辑片段、自定义合并分隔符、Windows 托盘和可配置全局快捷键。
- v0.3：可选的系统密钥保护、图片/文件历史、导入导出策略。
- v1.0：稳定的数据迁移、无障碍改进、签名桌面安装包。

## License

[MIT](LICENSE)
