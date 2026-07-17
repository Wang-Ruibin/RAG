# CampusQA：河海大学校园知识问答助手

CampusQA 是一个面向希望了解河海大学的普通用户与知识库管理员的中文 LLM + RAG Web 应用。系统把
1,027 篇版本化校园资料解析、清洗、切块并写入课件要求的 FAISS 向量知识库，通过
`bge-small-zh-v1.5`、中文 BM25、RRF 和 `bge-reranker-base` 找到原文，再由 DeepSeek
生成带来源编号的回答。本地知识库不能完整回答河海大学相关问题时，可回退到无需 API
Key 的免费多引擎搜索，也可按配置改用百度 AI Search；与河海大学无关的问题不会联网，
而是由范围策略礼貌拒答。用户确认满意的回答可异步清洗后热加入知识库。

当前仓库实现课程实训 MVP。默认问答链路是可评测、低延迟的直接 RAG；LangGraph 单
Agent 是指标达标后的增强路线，不阻塞本项目部署与验收。

当前 `misaki` 版本已于 2026-07-17 完成自动化检查、生产式启动回归和用户验收。

## 1. 已实现功能

- 邮箱注册、登录、Argon2 密码哈希、JWT、普通用户/管理员角色和账号启停。数据库仍保留
  `STUDENT` 枚举值以兼容现有账号。
- 所有登录用户可分页浏览、预览和下载 Markdown/TXT/PDF/DOCX 知识文档；上传、
  元数据修改、重新处理和完整删除仍仅限管理员。预览文本按内容哈希缓存。
- 标题层级感知切块、512 维 BGE 向量、稳定 chunk/vector ID、FAISS 余弦检索和中文
  BM25。
- Dense Top20 + BM25 Top20 + RRF Top12 + Cross-Encoder 精排，并按绝对分数与相对分差
  过滤弱相关上下文，最多保留 5 条来源。
- 同步问答与 POST SSE 流式问答、来源卡片、多轮会话、停止生成和异常状态持久化。
- 本地 RAG 证据不足时先判断问题范围：河海大学相关问题可回退到免费网页搜索（或可选
  百度 AI Search），网页来源使用独立 `[W1..W5]`；校外问题直接使用多样化礼貌回复，
  不发起网页请求。搜索超时、鉴权或额度异常会安全降级为拒答。
- 打开问答页或新建会话时主动显示随机问候和自我介绍；“你好/谢谢/再见”等社交消息
  也在本地响应，不消耗联网搜索或 LLM 调用。
- 用户可把已完成的有效回答加入知识库：后台清洗后写入独立的隐藏 QA 快速索引；知识库
  来源只建立关联，网页来源分别归档。强相似问题只加载关联原文并调用一次模型重新组织，
  跳过全量 RAG 和再次联网；最终引用只指向原知识文档或网页归档，不显示 QA 条目。
- QA 优先检索会在本地去除问句标点、补全省略的“河海大学”主语，并扩展少量高置信同义
  问法后取最高匹配分；不额外调用模型做问题改写，避免增加 Token、网络延迟和不稳定性。
- 回答卡片支持复制、点赞入库和倒赞纠错。纠错经管理员编辑/批准后生成普通
  `USER_CORRECTION` Markdown 文档，进入常规 FAISS/BM25 索引而不进入隐藏 QA 快速层。
- 引用组默认折叠。仅当次实时网页使用黄色 `[Wx]`；本地文档、网页归档和已审核
  用户纠错统一使用蓝色 `[Sx]`。
- React 19 + TypeScript + Ant Design 管理端和聊天端，安全 Markdown 与移动端适配。
- 50 条版本化评测集、阈值校准脚本，以及不消耗真实 Token 的 Fake LLM 接口测试。
- Windows、Linux、macOS、WSL 可共用的 Python 启动入口；支持纯 CPU 或 NVIDIA CUDA。

## 2. 技术架构与数据边界

```text
浏览器（React）
  ├─ JSON API：认证、用户、文档、会话、统计
  └─ POST SSE：start → status/delta → final sources → done/error
                       │
                  FastAPI 服务
       ┌───────────────┴────────────────┐
       │                                │
MySQL 业务数据库                 独立向量知识库
用户/权限/任务/会话/消息/纠错  NPZ 文档工件 → FAISS + BM25
                                       │
                         BGE Embedding → RRF → Reranker
                                       │证据不足
                              河海大学范围策略
                         校外礼貌拒答 ↙      ↘ 校内问题
                                  免费搜索 / 百度 AI Search（可选）
                                       │
                                DeepSeek + 引用校验
```

必须保持以下不变量：

- MySQL 只保存用户、权限、文档任务元数据、会话和问答历史，不保存资料正文、chunk、
  embedding 或向量。测试使用临时 SQLite 复用相同业务模型。
- `data/knowledge_base/documents/*.npz` 是每篇知识资料的可恢复工件；FAISS
  `IndexIDMap2(IndexFlatIP)` 和 BM25 是可重建派生索引。
- 稳定 chunk ID 同时是 FAISS vector ID。更新或删除单篇资料不会重新嵌入其他文档。
- 检索到的资料是不可信输入，不能覆盖系统提示词；回答只能使用知识库依据。
- 本地知识事实（含已归档网页）必须带 `[Sx]`、当次实时网页事实必须带 `[Wx]` 引用；
  两类来源都没有依据时拒答，不使用模型内部记忆补齐。校外问题不进入网页搜索阶段。
- `.env`、密钥、口令、上传文件、索引、模型缓存和本机 AI 配置不得提交到 Git。

详细数据流见 [系统架构](docs/architecture.md)，接口见 [API 文档](docs/api.md)。

## 3. 支持的平台与硬件

| 环境 | Python 方案 | 推理设备 | 推荐依赖命令 |
|---|---|---|---|
| Windows 10/11 x64 | Python 3.11/3.12 + uv | CPU | `uv sync --extra cpu --extra dev` |
| Windows 10/11 x64 + NVIDIA | Python 3.11/3.12 + uv | CUDA 12.8/13.0 | `uv sync --extra cu128 --extra dev` 或 `--extra cu130` |
| Linux/WSL2 x64 | Python 3.11/3.12 + uv | CPU 或 NVIDIA CUDA | 与 Windows 相同 |
| macOS Intel/Apple Silicon | Python 3.11/3.12 + uv | CPU/MPS 由 PyTorch 管理 | 使用 `--extra cpu` |

项目保留 `faiss-cpu`，GPU 用来加速 BGE Embedding 和 Reranker；这比在 Windows 上强制
安装 FAISS GPU 更容易复现。`MODEL_DEVICE=auto` 时 Sentence Transformers 自动选择
可用设备；也可以显式设为 `cpu` 或 `cuda`。

CUDA 版本取决于显卡驱动，不取决于本机是否单独安装完整 CUDA Toolkit。先运行
`nvidia-smi`，再按 [PyTorch 安装选择器](https://pytorch.org/get-started/locally/)
确认驱动适合的构建。CUDA 12.8 适合兼容优先，CUDA 13.0 适合驱动较新的机器；依赖
索引的配置方式遵循 [uv 的 PyTorch 指南](https://docs.astral.sh/uv/guides/integration/pytorch/)。

## 4. 准备软件

部署机需要：

- Git。
- Python 3.11 或 3.12，推荐 64 位 CPython 3.11。
- [uv](https://docs.astral.sh/uv/getting-started/installation/) 0.5.3 或更高版本。
- Node.js 22 与 npm 10 或更高版本。
- MySQL 8 或更高版本；MySQL 可以安装在 Windows，也可以安装在 Linux/WSL。
- 首次下载 Python/npm 依赖和两个 BGE 模型时可访问网络。

不需要 Java、Spring Boot、Redis、Docker 或独立向量数据库服务。开发测试可以使用
SQLite，但完整演示默认使用 MySQL。

## 5. 从零本地部署

以下命令都从仓库根目录执行。硬件 extra 只在 `uv sync` 时选择一次，后续用
`uv run --no-sync` 调用当前 `.venv`，避免 uv 在运行命令时把已经选好的 CPU/CUDA 构建
重新解析成另一种构建。这样不需要手动激活环境，PowerShell、CMD、Linux、macOS 和
WSL 的命令基本一致。

### 5.1 获取 `misaki` 分支

```bash
git clone --branch misaki --single-branch https://github.com/Wang-Ruibin/RAG.git
cd RAG
```

已有仓库可执行：

```bash
git fetch origin
git switch misaki
git pull --ff-only origin misaki
```

### 5.2 创建当前目录的 `.venv` 并安装后端

CPU 部署（所有平台默认推荐）：

```bash
uv sync --extra cpu --extra dev
```

Windows/Linux/WSL 的 NVIDIA GPU 部署，三种硬件 extra 只能选择一个：

```bash
# 驱动兼容优先
uv sync --extra cu128 --extra dev

# 新驱动机器
uv sync --extra cu130 --extra dev
```

`uv` 会在仓库根目录创建或复用 `.venv`，并严格按 `uv.lock` 安装。切换 CPU/CUDA 时
直接运行新的 `uv sync --extra ...` 即可；不要同时传入 `cpu`、`cu128`、`cu130`。

如果合作方暂时不能安装 uv，可使用兼容导出文件：

```bash
# 先用 python/py 创建根目录 .venv 并激活，再选择一个文件
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps

# NVIDIA CUDA 12.8：把第一行替换为
python -m pip install -r requirements-cu128.txt

# NVIDIA CUDA 13.0：把第一行替换为
python -m pip install -r requirements-cu130.txt
```

Windows PowerShell 创建和激活环境的等价命令是：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux/macOS/WSL 等价命令是：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

`pyproject.toml + uv.lock` 是权威依赖定义，三个 `requirements*.txt` 只是锁文件的
pip 兼容导出。维护者升级依赖后必须同时重新导出它们。

### 5.3 验证 CPU/GPU

```bash
uv run --no-sync python -c "import torch; print('torch=', torch.__version__); print('cuda=', torch.cuda.is_available()); print('device=', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

GPU 版若仍显示 `cuda=False`，先检查 `nvidia-smi` 和 Windows/WSL 显卡驱动，再确认安装
的是 `cu128` 或 `cu130` extra。CPU 部署无需处理该提示。

### 5.4 创建 MySQL 数据库

在 MySQL Shell、Workbench 或其他管理工具中执行：

```sql
CREATE DATABASE campus_qa CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

建议为应用单独创建最小权限账号，不要把真实密码写进 README、脚本、Git 提交或终端
截图。应用使用 SQLAlchemy `URL.create` 组装连接，密码含 `@`、`:` 等字符时无需自行
URL 编码。

#### WSL 能否访问 Windows 安装的 MySQL？

可以。本项目已经实测 WSL 通过 `127.0.0.1:3306` 访问 Windows MySQL。换电脑后按以下
顺序排查：

1. 在 Windows 服务管理器确认 MySQL 服务已启动。
2. 先在 WSL 测试 `mysql -h 127.0.0.1 -P 3306 -u 用户名 -p`。
3. 若 localhost 转发不可用，在 WSL 执行 `ip route show default`，把输出的网关地址填
   入 `.env` 的 `MYSQL_HOST`。
4. 确认 MySQL 监听地址、Windows 防火墙和账号允许该来源主机访问。
5. 只允许本机/局域网所需范围，不要把 3306 暴露到公网。

Windows 原生运行后端时通常直接使用 `MYSQL_HOST=127.0.0.1`。

### 5.5 配置环境变量

复制模板：

```bash
# Linux/macOS/WSL/Git Bash
cp .env.example .env
```

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

只编辑本机 `.env`。至少填写 `MYSQL_USER`、`MYSQL_PASSWORD`、`MYSQL_DATABASE`、
`JWT_SECRET` 和重新创建的 `DEEPSEEK_API_KEY`。生成 JWT 随机值的跨平台命令：

```bash
uv run --no-sync python -c "import secrets; print(secrets.token_urlsafe(48))"
```

主要配置如下：

| 变量 | 示例/默认含义 | 是否敏感 |
|---|---|---:|
| `DEEPSEEK_API_KEY` | DeepSeek 新建的 API Key | 是 |
| `LLM_BASE_URL` | `https://api.deepseek.com` | 否 |
| `LLM_MODEL` | 默认 `deepseek-v4-flash` | 否 |
| `JWT_SECRET` | 至少 32 字符的随机值 | 是 |
| `INITIAL_ADMIN_EMAIL` | 首个管理员邮箱 | 否 |
| `INITIAL_ADMIN_PASSWORD` | 可留空，由 CLI 安全交互输入 | 是 |
| `DB_BACKEND` | 完整演示使用 `mysql` | 否 |
| `MYSQL_HOST/PORT` | MySQL 地址与端口 | 否 |
| `MYSQL_USER/PASSWORD` | MySQL 登录信息 | 密码是 |
| `MYSQL_DATABASE` | 默认 `campus_qa` | 否 |
| `DATABASE_URL` | 可选，覆盖全部数据库分项 | 通常是 |
| `DATA_DIR` | 上传和知识库运行数据，默认 `./data` | 否 |
| `KNOWLEDGE_DIR` | 初始语料目录，默认 `./knowledge_docs` | 否 |
| `FRONTEND_DIST` | 前端构建目录，默认 `./frontend/dist` | 否 |
| `EMBEDDING_MODEL` | BGE 512 维中文向量模型 | 否 |
| `RERANKER_MODEL` | BGE Cross-Encoder 精排模型 | 否 |
| `MODEL_DEVICE` | `auto`、`cpu` 或 `cuda` | 否 |
| `MODEL_LOCAL_FILES_ONLY` | 模型缓存完成后可设 `true` 离线演示 | 否 |
| `RAG_PREWARM` | 启动时预热本地模型，避免首次问答承担冷启动耗时 | 否 |
| `RERANK_ENABLED` | 是否启用本地精排 | 否 |
| `RETRIEVAL_MIN_SCORE` | 评测集校准的拒答阈值 | 否 |
| `RETRIEVAL_LEXICAL_*` | 关键词覆盖、Dense/BM25 排名共同支持的边界命中放行条件 | 否 |
| `RETRIEVAL_CONTEXT_MIN_SCORE` | 后续上下文来源的最低精排分，默认 `0.60` | 否 |
| `RETRIEVAL_CONTEXT_SCORE_MARGIN` | 后续来源与最高分允许的最大分差，默认 `0.20` | 否 |
| `DENSE/SPARSE/FUSION/CONTEXT_TOP_K` | 各检索阶段候选数量；最终上下文最多 5 条 | 否 |
| `WEB_SEARCH_ENABLED` | 本地知识库低置信度时是否回退网页搜索，默认 `true` | 否 |
| `WEB_SEARCH_PROVIDER` | 默认 `free`，也可设为 `baidu` | 否 |
| `FREE_SEARCH_*` | 地区、安全级别、时效、后端、数量和超时；无需 Key | 否 |
| `BAIDU_SEARCH_API_KEY` | 仅选择百度提供者时需要的 API Key | 是 |
| `BAIDU_SEARCH_*` | 百度搜索数量、过滤和超时等可选配置 | 部分是 |
| `ANSWER_KNOWLEDGE_CATEGORY` | 满意回答热加入后的文档分类，默认“问答沉淀” | 否 |
| `QA_RETRIEVAL_*` | QA 优先召回数量、直接命中与辅助命中阈值 | 否 |
| `QA_DEDUPE_MIN_SCORE` | QA 语义去重阈值，默认 `0.97` | 否 |
| `QA_TIME_SENSITIVE_MAX_AGE_DAYS` | 时效问题允许直接复用 QA 的最长天数 | 否 |
| `EVIDENCE_SUFFICIENCY_CHECK_ENABLED` | 检查本地资料能否真正回答问题 | 否 |
| `FRONTEND_ORIGINS` | 开发模式允许的前端来源 | 否 |

任何曾经出现在聊天、截图或提交里的旧 Key 都应先在服务商控制台撤销，再创建新 Key。

默认配置无需任何搜索密钥即可联网搜索。需要显式覆盖时，可在本地 `.env` 中增加：

```dotenv
WEB_SEARCH_ENABLED=true
WEB_SEARCH_PROVIDER=free
FREE_SEARCH_REGION=cn-zh
FREE_SEARCH_BACKEND=auto
```

免费模式使用 MIT 许可的 `ddgs` 非官方多引擎客户端；默认 `auto` 会自动选择当前网络
可用且无需 Key 的搜索后端。该方案免费但可能受到限流或搜索页面变化影响，异常会
安全降级为拒答。若改用百度，设置
`WEB_SEARCH_PROVIDER=baidu` 和 `BAIDU_SEARCH_API_KEY`。设为 `WEB_SEARCH_ENABLED=false`
则维持原有本地 RAG + 低置信拒答行为。

### 5.6 初始化表结构和管理员

```bash
uv run --no-sync alembic upgrade head
uv run --no-sync python -m app.cli create-admin --email admin@campusqa.cn
```

CLI 默认安全地交互读取管理员密码。自动演示也可把 `INITIAL_ADMIN_PASSWORD` 只放在被
Git 忽略的 `.env` 中；不要通过 `--password` 把真实密码留在 shell 历史。

### 5.7 安装并构建前端

```bash
cd frontend
npm ci
npm run build
cd ..
```

`npm ci` 按 `package-lock.json` 重建依赖，生产文件输出到被 Git 忽略的
`frontend/dist/`，FastAPI 启动后会托管它。

### 5.8 首次导入知识库

```bash
uv run --no-sync python -m app.cli index knowledge_docs --admin-email admin@campusqa.cn
```

首次执行会下载两个 BGE 模型。全量处理 1,027 篇资料在 CPU 上耗时较长，GPU 可明显
加快 Embedding 和精排预热。导入可重复执行：内容哈希相同的文档会跳过，失败文件会
输出清单，完成后从知识工件原子重建 FAISS/BM25。

生产启动脚本也会在 Uvicorn 启动前幂等执行这一步：数据库中已有的内容按哈希跳过，
运行期间从知识库删除的文档会立即从 NPZ、FAISS 和 BM25 中移除；如果对应源文件仍保留
在 `knowledge_docs/`，则下次重启服务时会重新导入。运行期间不会监视本地目录或自动回填。

用命令行验证原文检索：

```bash
uv run --no-sync python -m app.cli query "2026年9月计算机等级考试何时报名？"
```

### 5.9 启动生产式本地服务

Windows、Linux、macOS 和 WSL 通用：

```bash
uv run --no-sync python scripts/start.py
```

Linux/macOS/WSL 也可以使用：

```bash
bash scripts/start.sh
```

打开 <http://127.0.0.1:8000>，Swagger 位于
<http://127.0.0.1:8000/docs>，健康检查位于
<http://127.0.0.1:8000/api/health>。启动脚本默认只监听本机 `127.0.0.1`，终端会显示
`Uvicorn running on http://127.0.0.1:8000`。修改地址或端口可在运行前设置 `HOST`、
`PORT` 环境变量；只有确实需要局域网访问时才设置 `HOST=0.0.0.0`。

两个模型成功缓存并完成一次查询预热后，断网演示可在 `.env` 设置：

```dotenv
MODEL_LOCAL_FILES_ONLY=true
```

## 6. 开发模式

后端终端：

```bash
uv run --no-sync uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

前端终端：

```bash
cd frontend
npm run dev
```

访问 <http://127.0.0.1:5173>。Vite 将 `/api` 代理到 FastAPI。生产部署不需要单独运行
Vite，只需要先 `npm run build`，再运行跨平台启动脚本。

常用管理命令：

```bash
uv run --no-sync alembic current
uv run --no-sync alembic upgrade head
uv run --no-sync python -m app.cli create-admin
uv run --no-sync python -m app.cli index knowledge_docs
uv run --no-sync python -m app.cli query "你的问题"
```

## 7. 测试、评测与发布检查

后端静态检查和测试：

```bash
uv run --no-sync ruff check backend evals scripts
uv run --no-sync pytest --cov=app --cov-report=term-missing
```

前端检查：

```bash
cd frontend
npm run lint
npm run test -- --run
npm run build
cd ..
```

真实检索评测：

```bash
uv run --no-sync python evals/run_eval.py --mode dense --output docs/evaluation_dense.json
uv run --no-sync python evals/run_eval.py --mode hybrid --output docs/evaluation_hybrid.json
uv run --no-sync python evals/run_eval.py --mode hybrid-rerank --output docs/evaluation_report.json
```

确认 API Token 成本后才运行生成评测：

```bash
uv run --no-sync python evals/run_eval.py --with-generation
uv run --no-sync python -m app.smoke
```

GitHub 发布前：

```bash
uv run --no-sync python scripts/check_secrets.py
git status --short
git diff --check
```

2026-07-15 的 CPU 评测基线为 1,026 篇、3,867 个 chunk；50 条评测达到 Hit@5 0.950、
MRR@5 0.919、P95 1.462 秒、知识库外误接受率 0%。2026-07-17 当前运行状态为 1,035 篇
READY 文档（1,027 篇版本化语料 + 8 篇网页归档）、3,883 个 chunk、3 条隐藏 QA；尚未
用新增语料和归档文档重跑整套检索评测，因此原始 JSON 与历史基线指标保持不变。
当前自动化基线为后端 54 项、前端 9 项。完整条件和指标解释见
[评测总结](docs/evaluation_summary.md)。自动化检查、生产式启动与手工验收均已通过。

## 8. 项目结构树

下面列出所有代码、配置、测试和说明文件。`knowledge_docs/` 的 1,027 个语料文件按分类
整体说明，不在 README 重复展开每个长文件名；`data/`、`.venv/`、`node_modules/`、
`frontend/dist/` 是本机运行目录，不进入仓库。

```text
.
├── .env.example                    环境变量安全模板
├── .github/CODEOWNERS              GitHub 代码所有者配置
├── .gitignore                      密钥、数据、缓存和构建产物忽略规则
├── README.md                       部署、协作和文件导航（本文件）
├── alembic.ini                     Alembic 迁移入口配置
├── pyproject.toml                  Python 项目、依赖、CPU/CUDA extra 和工具配置
├── uv.lock                         全平台可重复安装锁文件（权威）
├── requirements.txt                pip CPU 运行时兼容导出
├── requirements-cu128.txt          pip NVIDIA CUDA 12.8 兼容导出
├── requirements-cu130.txt          pip NVIDIA CUDA 13.0 兼容导出
├── backend/
│   ├── alembic/
│   │   ├── env.py                  迁移运行环境和数据库连接
│   │   ├── script.py.mako          新迁移模板
│   │   └── versions/
│   │       ├── 20260715_0001_initial.py  初始业务表迁移
│   │       ├── 20260716_0002_answer_knowledge_web_origin.py 回答入库与来源类型
│   │       ├── 20260717_0003_hidden_qa_index.py 隐藏 QA 快速索引
│   │       └── 20260717_0004_answer_corrections.py 用户纠错与审核数据
│   ├── app/
│   │   ├── __init__.py             Python 包标记
│   │   ├── main.py                 FastAPI 组装、生命周期、路由和前端托管
│   │   ├── cli.py                  管理员、全量导入和检索调试 CLI
│   │   ├── smoke.py                真实登录、同步问答和 SSE 冒烟脚本
│   │   ├── api/
│   │   │   ├── __init__.py         API 包标记
│   │   │   ├── dependencies.py     当前用户、管理员和数据库依赖
│   │   │   ├── auth.py             注册、登录和当前用户接口
│   │   │   ├── admin.py            管理员用户列表与角色/状态修改
│   │   │   ├── documents.py        知识文档 CRUD、上传和重处理接口
│   │   │   ├── chat.py             同步/SSE 问答和会话接口
│   │   │   └── system.py           健康检查与统计接口
│   │   ├── core/
│   │   │   ├── __init__.py         核心包标记
│   │   │   ├── config.py           `.env` 配置、路径、设备和运行时校验
│   │   │   ├── database.py         SQLAlchemy engine/session 和初始化
│   │   │   ├── security.py         Argon2、JWT 和认证安全逻辑
│   │   │   └── responses.py        统一 JSON 响应封装
│   │   ├── models/
│   │   │   ├── __init__.py         模型导出
│   │   │   ├── enums.py            角色、文档阶段和消息状态枚举
│   │   │   ├── orm.py              SQLAlchemy 业务表模型
│   │   │   └── schemas.py          Pydantic 请求/响应与 SourceRef 类型
│   │   ├── rag/
│   │   │   ├── __init__.py         RAG 包标记
│   │   │   ├── parser.py           Markdown/TXT/PDF/DOCX 解析与网页噪声清洗
│   │   │   ├── chunker.py          标题感知和递归重叠切块
│   │   │   ├── embedding.py        BGE 文档/问题向量化与设备选择
│   │   │   ├── index.py            NPZ 工件、FAISS/BM25 和原子索引恢复
│   │   │   ├── qa_index.py         隐藏 QA 原子工件与小型 FAISS 索引
│   │   │   ├── retrieval.py        Dense/BM25 并行召回、RRF 和精排
│   │   │   └── generation.py       DeepSeek 流式生成、Prompt 与引用校验
│   │   └── services/
│   │       ├── __init__.py         服务包标记
│   │       ├── documents.py        上传、预览、CRUD 和知识工件业务流程
│   │       ├── chat.py             会话、检索、联网与生成编排
│   │       ├── chat_scope.py       校内范围判断、社交回复和拒答文案策略
│   │       ├── message_context.py  回答入库/纠错共用的会话问题定位
│   │       ├── qa_knowledge.py     QA 改写、命中分层和来源解析
│   │       ├── answer_knowledge.py 点赞回答去重、QA 入库和网页归档
│   │       ├── answer_corrections.py 倒赞纠错、审核和普通文档入库
│   │       └── web_search.py       免费/百度搜索提供者与安全降级
│   └── tests/
│       ├── conftest.py             临时 SQLite、隔离数据目录和 HTTP client fixture
│       ├── test_config.py           MySQL URL、密钥占位和设备配置测试
│       ├── test_api.py              认证、权限、问答、引用和会话 API 测试
│       ├── test_document_api.py     知识库只读权限、预览/下载与管理 CRUD 测试
│       ├── test_answer_corrections.py 纠错提交、审批、入库与删除回归
│       ├── test_answer_knowledge.py 点赞入库、QA 去重和网页归档测试
│       ├── test_web_search.py       免费/百度搜索、异常分类与规范化测试
│       ├── test_documents.py        文档后台处理和知识工件测试
│       └── test_rag_units.py        解析、切块、RRF 与引用校验单元测试
├── frontend/
│   ├── index.html                   Vite HTML 入口
│   ├── package.json                 npm 脚本和前端直接依赖
│   ├── package-lock.json            npm 可重复安装锁文件
│   ├── eslint.config.js             ESLint 规则
│   ├── tsconfig.json                TypeScript 工程引用入口
│   ├── tsconfig.app.json            浏览器应用 TypeScript 配置
│   ├── tsconfig.node.json           Vite/Node 配置文件的 TypeScript 配置
│   ├── vite.config.ts               React 插件、测试环境和 API 代理
│   └── src/
│       ├── main.tsx                 React 挂载入口
│       ├── App.tsx                  路由、鉴权和管理员页面保护
│       ├── types.ts                 API、会话、文档和 SSE 类型
│       ├── styles.css               全局布局、聊天、管理页和响应式样式
│       ├── context/AuthContext.tsx  Token、当前用户和登录状态上下文
│       ├── lib/api.ts               JSON API client 与统一错误处理
│       ├── lib/sse.ts               POST ReadableStream SSE 解析器
│       ├── lib/sse.test.ts          SSE 分帧和异常解析 Vitest
│       ├── components/SourceCards.tsx  引用编号、标题、日期、片段与官网链接
│       ├── components/SourceCards.test.tsx 引用折叠和 S/W 颜色测试
│       └── pages/
│           ├── LoginPage.tsx        登录/注册页面
│           ├── ChatPage.tsx         欢迎语、流式聊天、历史和回答反馈
│           ├── ChatPage.test.tsx    欢迎语、来源标识和反馈交互测试
│           ├── DocumentsPage.tsx    全员知识库浏览/预览与管理维护页面
│           ├── DocumentsPage.test.tsx 只读权限和管理员操作测试
│           ├── CorrectionReviewPage.tsx 管理员回答纠错审核页面
│           └── UsersPage.tsx        管理员角色和启停管理页面
├── evals/
│   ├── campus_qa.jsonl              30 知识问答 + 10 多轮 + 10 无答案样本
│   └── run_eval.py                  Dense/Hybrid/Rerank/生成评测与阈值校准
├── docs/
│   ├── architecture.md              组件、数据边界、索引一致性和数据流
│   ├── api.md                       JSON API、SourceRef 和 SSE 协议
│   ├── testing.md                   自动化、真实评测和安全冒烟说明
│   ├── evaluation_summary.md        参数对比、最终指标和局限
│   ├── evaluation_*.json            各检索/精排实验的原始可复查报告
│   ├── demo_and_defense.md          5–6 分钟演示、答辩要点和故障预案
│   ├── project_journal.md           制作过程、决策、验证与后续 PPT 素材
│   └── agent_roadmap.md             LangGraph 只读单 Agent 长期路线
├── scripts/
│   ├── start.py                     Windows/Linux/macOS/WSL 通用生产入口
│   ├── start.sh                     Bash 启动包装器
│   ├── migrate_legacy_qa.py         旧回答文档迁移为隐藏 QA 的一次性工具
│   └── check_secrets.py             Git 发布前的密钥与口令痕迹扫描
├── knowledge_docs/                  1,027 篇版本化河海大学知识资料
│   ├── academic/                    教务、课程和培养通知
│   ├── academic_files/              教务附件转换出的文本资料
│   ├── admin/                       学校管理、招生与行政通知
│   ├── alumni/                      校友信息
│   ├── campus_life/                 校园生活与服务
│   ├── departments/                 院系和部门资料
│   ├── news/                        校园新闻
│   ├── research/                    科研通知与成果
│   ├── third_party/                 经筛选的外部公开资料
│   └── university_info/             学校概况和组织信息
└── data/                             本机上传、NPZ 工件与 FAISS/BM25 索引（Git 忽略）
```

## 9. 协作开发约定

- Python 业务代码放在 `backend/app`，测试放在 `backend/tests`；不要把正文或向量写入
  MySQL。
- 前端只能通过 API/SSE 使用后端；管理员 UI 隐藏不能代替后端权限校验。
- 新文档格式先补 parser/chunker 测试，再修改导入流程。
- 修改检索参数必须保存评测报告，不得仅凭单个示例调阈值。
- 修改数据库模型必须新增 Alembic migration，不得只改 ORM。
- 修改依赖时先更新 `pyproject.toml`/`package.json`，再更新锁文件；不要手工把未验证的
  浮动版本写进 requirements。
- 提交前执行后端测试、前端 lint/test/build、`git diff --check` 和密钥扫描。
- 不提交 `.env`、`AGENTS.md`、Claude/Codex/Cursor 本机配置、数据库、日志、上传文件、
  模型、缓存、FAISS 索引或前端构建产物。

## 10. 依赖维护

Python 依赖升级流程：

```bash
uv lock --upgrade
uv sync --extra cpu --extra dev
uv run --no-sync pytest

uv export --format requirements.txt --no-hashes --no-dev --extra cpu --emit-index-url --no-emit-project --locked --output-file requirements.txt
uv export --format requirements.txt --no-hashes --no-dev --extra cu128 --emit-index-url --no-emit-project --locked --output-file requirements-cu128.txt
uv export --format requirements.txt --no-hashes --no-dev --extra cu130 --emit-index-url --no-emit-project --locked --output-file requirements-cu130.txt
```

前端依赖升级流程：

```bash
cd frontend
npm update
npm run lint
npm run test -- --run
npm run build
```

依赖“最新”以锁文件生成时各官方索引中满足 `pyproject.toml` 兼容范围、并通过本项目
测试的版本为准，而不是在部署时无约束地下载未来版本。遇到 PyTorch/CUDA 组合变化时，
先查看官方兼容矩阵，再更新 extra 和三份导出文件。

## 11. 常见问题

### FastAPI 启动后只有 JSON，没有页面

先执行 `cd frontend && npm ci && npm run build`。`scripts/start.py` 会在缺少
`frontend/dist/index.html` 时直接给出提示。

### 连接 MySQL 失败

确认 `.env` 使用 `DB_BACKEND=mysql`，服务已启动，数据库已创建，并检查 host、port、
账号来源权限和防火墙。WSL 访问 Windows MySQL 时优先试 `127.0.0.1`，再试 Windows
网关地址。

### `faiss` 或 PyTorch 安装失败

确认使用 64 位 Python 3.11/3.12，并只选择一个硬件 extra。Windows 不使用 Linux 的
`.venv/bin/...` 路径，直接运行 `uv run --no-sync ...`。CUDA 失败时先回退 CPU 完成部署，再单独
核对驱动和 PyTorch 构建。

### 模型下载慢或断网演示失败

保持 `MODEL_LOCAL_FILES_ONLY=false` 完成首次导入和查询，让 Hugging Face 缓存两个
模型；确认预热成功后再改为 `true`。模型缓存属于本机数据，不提交到 GitHub。

### 修改知识文档后没有生效

管理员页面点击“重新处理”，或重新运行全量 `index` 命令。直接改
`knowledge_docs/` 不会绕过导入状态机自动写入运行索引。

## 12. 答辩与后续路线

- [演示与答辩脚本](docs/demo_and_defense.md)
- [制作过程和 PPT 素材日志](docs/project_journal.md)
- [测试与安全边界](docs/testing.md)
- [Agent 长期路线](docs/agent_roadmap.md)

MVP 后计划保留直接 RAG 快速路径，仅对多条件、比较和办事规划问题启用 LangGraph
单 Agent。Agent 只开放只读检索/元数据/政策比较/当前日期工具，最多 4 次调用，最终回答
仍必须经过引用校验。暂不做多 Agent、自动写数据库或自动执行校园事务。
