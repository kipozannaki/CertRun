# CertRun

> Self-service finisher certificate platform for races · Three-step coordinate picker + batch generation + mobile-first lookup

完赛证书生成与查询系统 · 三分步坐标拾取 · 批量生成 · 手机端自助查询

---

## 中文

**CertRun** 是一个面向校园/小型赛事完赛证书发放的轻量平台。它把"批量生成证书"和"选手自助查证"拆成两个完全解耦的子系统，通过一个共享的证书目录互通——管理端**只**管生成，客户端**只**管查询，前后端从部署到代码都互不依赖。

### 核心特性

- 🎯 **三分步坐标拾取**：网页端打开模板图，依次点击"姓名 / 完赛时间 / 参赛号"的下划线起点，坐标自动保存
- 📊 **Excel 批量注入**：上传 `姓名 | 参赛号 | 成绩` 三列的 xlsx，一键批量生成证书
- 📱 **手机端查询**：选手输入姓名 + 参赛号即可看到自己的证书，PC/手机全适配
- 🏎️ **性能优化**：模板图只解码一次、客户端走 `index.json` O(1) 索引、查询防抖 + AbortController
- 🔒 **路径安全**：拒绝 `../` 路径遍历攻击

### 架构

```
MaraProject/
├── admin/                # 管理端：5001 端口
│   ├── app.py            # Flask 入口
│   ├── core.py           # 模板解码 / xlsx 解析 / 证书生成 / 索引维护
│   ├── inject.py         # CLI 批量生成工具
│   ├── pick_coords.py    # 坐标拾取工具
│   └── templates/        # 三分步生成器前端
├── client/               # 客户端：5000 端口
│   ├── app.py            # Flask 入口
│   ├── core.py           # 索引查询
│   └── templates/        # 查询页面
└── certificates/         # 共享目录：生成的证书 + index.json
```

两端通过 `SHARED_DIR = os.path.dirname(BASE_DIR)` 自动指向同一个 `certificates/` 文件夹。

### 快速开始

```bash
# 1. 启动管理端（端口 5001）
cd admin
pip install -r requirements.txt
python app.py

# 2. 另开终端启动客户端（端口 5000）
cd ../client
pip install -r requirements.txt
python app.py
```

打开浏览器：
- 管理端：<http://127.0.0.1:5001> — 上传模板 → 拾取三个坐标 → 上传 xlsx → 一键生成
- 客户端：<http://127.0.0.1:5000> — 输入姓名+参赛号 → 查看/下载证书

### 自备资源

`.gitignore` 排除了以下文件，使用时需自行放置：

| 路径 | 用途 | 来源 |
|---|---|---|
| `admin/msyhbd.ttc` | 中文字体（微软雅黑 Bold） | 从 `C:\Windows\Fonts\` 复制 |
| `admin/template.jpg` | 证书模板图 | 用户自行准备 |
| `admin/参赛成绩.xlsx` | 成绩表 | 列：`姓名 \| 参赛号 \| 成绩` |

### 工作流

```
[管理端] 选模板图 → 拾取三个坐标 → 上传 xlsx → 批量生成 → 写 index.json
                                                    ↓
                            [共享 certificates/ 目录]
                                                    ↓
[客户端] 选手输入姓名+参赛号 → 查 index.json → 返回证书 PNG
```

### CLI 工具

```bash
# 坐标拾取（命令行版，调试用）
python admin/pick_coords.py

# 批量生成证书（命令行版，绕过 Web 界面）
python admin/inject.py
```

### 技术栈

- **后端**：Python 3.11 / Flask 2.3+
- **图像处理**：Pillow 10+
- **Excel 解析**：openpyxl 3+
- **前端**：原生 HTML + CSS + JavaScript（无框架依赖）

### 路线图

- [ ] SSE 流式推送真实生成进度
- [ ] 证书缩略图
- [ ] 一次性分享链接（HMAC 签名）
- [ ] Docker 一键部署
- [ ] pytest 单测覆盖

### 许可证

MIT

---

## English

**CertRun** is a lightweight platform for issuing finisher certificates at campus / small-scale races. It splits the workflow into two fully-decoupled subsystems — a generation side and a self-service lookup side — that share only a `certificates/` directory on disk. The two projects have no runtime dependencies on each other.

### Features

- 🎯 **Three-step coordinate picker**: open the template in the browser, click the underline starting points for *name / time / bib* in sequence — coordinates are auto-saved
- 📊 **Batch generation from xlsx**: upload a `name | bib | time` spreadsheet, generate every certificate in one click
- 📱 **Mobile-first lookup**: athletes enter their name + bib to view and download their certificate, responsive on phone & desktop
- 🏎️ **Performance-tuned**: template image decoded once, client queries an `index.json` for O(1) lookup, debounced fetches with `AbortController`
- 🔒 **Path-traversal hardening**: rejects `../` payloads at the client side

### Architecture

```
MaraProject/
├── admin/                # Admin (port 5001)
│   ├── app.py            # Flask entry
│   ├── core.py           # image / xlsx / generation / index
│   ├── inject.py         # CLI batch generator
│   ├── pick_coords.py    # CLI coordinate picker
│   └── templates/        # 3-step generator UI
├── client/               # Athlete (port 5000)
│   ├── app.py            # Flask entry
│   ├── core.py           # index-based lookup
│   └── templates/        # lookup UI
└── certificates/         # shared: generated certs + index.json
```

Both projects resolve `SHARED_DIR = os.path.dirname(BASE_DIR)` so the same `certificates/` folder is automatically shared.

### Quick start

```bash
# Terminal 1 — Admin (port 5001)
cd admin
pip install -r requirements.txt
python app.py

# Terminal 2 — Athlete lookup (port 5000)
cd ../client
pip install -r requirements.txt
python app.py
```

Open in your browser:
- Admin: <http://127.0.0.1:5001> — upload template → pick 3 coords → upload xlsx → generate
- Athlete: <http://127.0.0.1:5000> — type name + bib → see your certificate

### User-supplied assets

The following are excluded from `.gitignore` and must be placed by the operator:

| Path | Purpose | Source |
|---|---|---|
| `admin/msyhbd.ttc` | Chinese font (Microsoft YaHei Bold) | copy from `C:\Windows\Fonts\` |
| `admin/template.jpg` | Certificate template | prepare yourself |
| `admin/参赛成绩.xlsx` | Results spreadsheet | columns: `name \| bib \| time` |

### Workflow

```
[Admin]  select template → pick 3 coords → upload xlsx → batch-generate → write index.json
                                                       ↓
                          [shared certificates/ directory]
                                                       ↓
[Athlete]  enter name + bib → look up index.json → receive certificate PNG
```

### CLI tools

```bash
# Coordinate picker (CLI, useful for debugging)
python admin/pick_coords.py

# Batch generator (CLI, bypasses the web UI)
python admin/inject.py
```

### Tech stack

- **Backend**: Python 3.11 / Flask 2.3+
- **Imaging**: Pillow 10+
- **Excel**: openpyxl 3+
- **Frontend**: vanilla HTML / CSS / JS (no framework)

### Roadmap

- [ ] SSE-streamed real progress
- [ ] Thumbnail previews
- [ ] HMAC-signed share links
- [ ] Docker one-liner deployment
- [ ] pytest coverage

### License

MIT
