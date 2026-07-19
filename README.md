# 🏫 CampusQA · 河海智问

<div align="center">

**基于 RAG + LLM 的校园知识智能问答系统**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Vue](https://img.shields.io/badge/Vue-3.x-4FC08D?logo=vuedotjs)](https://vuejs.org)
[![Spring Cloud](https://img.shields.io/badge/Spring%20Cloud-2023-6DB33F?logo=spring)](https://spring.io)
[![License](https://img.shields.io/badge/license-MIT-blue)](./LICENSE)

</div>

https://github.com/user-attachments/assets/placeholder

> 🤖 **河海智问**——输入你想了解的校园问题，AI 自动从 1000+ 篇校园文档中检索答案，支持联网搜索补充。不会的问题礼貌拒答，不瞎编。

---

## ✨ 核心功能

| 功能 | 说明 |
|------|------|
| 🔍 **智能问答** | 输入问题 → 向量检索 + BM25 混合召回 → RRF 融合 → Reranker 精排 → DeepSeek 生成带来源引用的回答 |
| 🌐 **联网搜索** | 本地知识库覆盖不足时，自动回退到多引擎免费搜索（DuckDuckGo），也可配置百度 AI Search |
| 📎 **来源标注** | 每个答案附带 `[S1][S2]` 知识库或 `[W1]` 网页引用，可点击查看原文出处 |
| 💬 **多轮对话** | 历史会话持久化，支持重命名、搜索，保留上下文连续问答 |
| 👍 **点赞·纠错** | 满意答案一键入库热加载；不满意可提交纠错，管理员审核后索引生效 |
| 👤 **访客模式** | 无需注册直接体验单轮问答，零痕迹不落库；注册后解锁全部功能 |
| 📚 **知识库管理** | 拖拽上传 MD/TXT/PDF/DOCX，自动解析→切块→向量化→入库，支持重新索引 |
| 🔐 **权限管控** | 基于 Sa-Token JWT 的统一认证，RBAC 角色权限，网关层集中鉴权 |
| 🎨 **青绿山水 UI** | 宣纸雾白底 + 石绿渐变 + 霞鹜文楷字体，千里江山图风格登录页 |

### 🧠 降级回答策略

```
用户提问
  ├─ 隐藏 QA 索引命中 → 核验关联证据是否充分
  │   ├─ 充分 → DeepSeek 直接生成
  │   └─ 不足 → 执行完整 RAG
  ├─ 完整 RAG（Dense + BM25 + RRF + Reranker）
  │   ├─ 本地证据充分 → DeepSeek 生成 + [Sx] 引用
  │   └─ 本地不足 → 河海大学相关问题？
  │       ├─ 是 → 联网搜索 → DeepSeek + [Wx]/[Sx] 混合引用
  │       └─ 否 → 礼貌拒答，不发起联网请求
  └─ 全部失败 → 拒答或范围外提示
```

---

## 🚀 快速开始（5 分钟跑起来）

### 前置环境

| 组件 | 版本 | 用途 |
|------|------|------|
| JDK | 17+ | 编译运行 Java 微服务 |
| Maven | 3.9+ | Java 项目构建 |
| Python | 3.11-3.12 | RAG 检索引擎 |
| uv | latest | Python 包管理（`pip install uv`） |
| Node.js | 18+ | 前端开发 |
| MySQL | 8.0 | 业务数据库 |
| Redis | 7.x | Token 缓存 + Session |
| Nacos | 2.4.x | 服务注册与配置中心 |

### 1. 克隆并安装依赖

```bash
git clone https://github.com/Wang-Ruibin/RAG.git campusqa
cd campusqa

# Python 依赖（首次需下载 BGE 模型，国内请设置 HF_ENDPOINT）
uv sync --extra cpu

# 前端依赖
cd campus-frontend && npm install && cd ..
```

### 2. 初始化数据库

```sql
CREATE DATABASE campus_qa DEFAULT CHARACTER SET utf8mb4;

-- 从项目提供的 init.sql 建表 + 初始数据
mysql -u root -p campus_qa < campus-backend/sql/init.sql

-- 已有库升级（增量脚本）
mysql -u root -p campus_qa < campus-backend/sql/upgrade-guest-mode.sql
```

### 3. 向量化知识库

```bash
uv run --no-sync alembic upgrade head
uv run --no-sync python -m app.cli index knowledge_docs --admin-email admin@campusqa.cn
```

> 📖 知识库包含 1,000+ 篇河海大学校园资料（招生、学院、后勤、图书馆、选课等）

### 4. 启动服务

按顺序启动四个服务：

```bash
# ① Nacos（注册中心）
# Windows: startup.cmd -m standalone
# macOS/Linux: sh startup.sh -m standalone

# ② Java 微服务（启动类在各自 src/main/java 下）
# 依次启动：campus-system(9201) → campus-auth(9210) → campus-gateway(19280)

# ③ Python RAG 引擎
set HF_HUB_OFFLINE=1
set DDGS_PROXY=http://127.0.0.1:7897          # 若不开联网搜索可省略
uv run --no-sync uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

# ④ Vue 前端（开发模式）
cd campus-frontend && npm run dev
```

> ⚠️ **Windows 用户**：启动 Python 服务前需在 cmd 中逐行执行 `set` 命令（不要用 bash 内联写法 `&&` 连接）。

### 5. 打开浏览器

访问 `http://localhost:5173`，用默认管理员账号登录：

| 账号 | 密码 |
|------|------|
| `admin` | `admin123` |

> 或直接点击登录页底部「访客进入」免注册体验问答。

---

## 🏗️ 技术栈

### 后端微服务（Java）

| 服务 | 端口 | 框架 | 职责 |
|------|------|------|------|
| campus-gateway | 19280 | Spring Cloud Gateway + Sa-Token Reactor | 统一入口、JWT 鉴权、路由转发 |
| campus-auth | 9210 | Spring Boot + Sa-Token | 登录/注册/验证码、JWT 签发 |
| campus-system | 9201 | Spring Boot + MyBatis-Plus | 用户/角色/菜单管理、操作日志 |

### RAG 检索引擎（Python FastAPI）

| 组件 | 技术选型 |
|------|----------|
| Web 框架 | FastAPI + SQLAlchemy (async) |
| 向量模型 | BGE-small-zh-v1.5（512 维） |
| 向量库 | FAISS (CPU，IndexIDMap2 + IndexFlatIP) |
| 关键词检索 | 中文 BM25（jieba 分词） |
| 融合排序 | RRF (Reciprocal Rank Fusion) |
| 精排模型 | BGE-Reranker-Base (Cross-Encoder) |
| LLM | DeepSeek V4 Flash（OpenAI 兼容接口） |
| 联网搜索 | DuckDuckGo（免费）/ 百度千帆 AI Search（可选） |
| 文档解析 | pypdf + python-docx |

### 前端（Vue3 TypeScript）

| 组件 | 技术选型 |
|------|----------|
| 框架 | Vue 3 + TypeScript |
| 构建 | Vite |
| UI 库 | Element Plus |
| 状态管理 | Pinia |
| HTTP | Axios（SSE 流式解析） |
| 设计 | 青绿山水 v3 — #0F9179→#52C79B 渐变 + 霞鹜文楷 |
| 路由 | Vue Router 4（动态菜单 + 权限守卫） |

### 整体架构

```
浏览器 (Vue3 + Element Plus)
  │
  ├─ /auth/** /system/**  ──→  Gateway (:19280)  ──→  campus-auth (:9210)
  │                                                    campus-system (:9201)
  │
  └─ /qa/** /knowledge/** ──→  Gateway ──→ Python FastAPI (:8000, 仅本地)
        (X-Login-Name 信任头)                 ├─ FAISS + BM25 检索
                                              ├─ DeepSeek 生成
                                              └─ MySQL (campus_qa 共库)
```

> 🔒 Python 端口只监听 `127.0.0.1`，不直接对外暴露。Gateway 鉴权通过后注入 `X-Login-Name` 信任头。

---

## 📁 项目结构

```
campusqa/
├── backend/                    # Python RAG 引擎 (FastAPI)
│   ├── app/
│   │   ├── api/                # chat, documents, admin 接口
│   │   ├── core/               # 配置、中间件、操作日志
│   │   ├── models/             # SQLAlchemy ORM
│   │   ├── prompt/             # 系统提示词（版本化）
│   │   ├── rag/                # 检索/生成/联网搜索
│   │   └── services/           # 问答编排服务
│   ├── alembic/                # 数据库迁移
│   ├── data/                   # 知识库工件 + 上传文件
│   └── tests/                  # 单元/API 测试
│
├── campus-backend/             # Java 微服务 (SpringCloud)
│   ├── campus-gateway/         # 网关（鉴权 + 路由）
│   ├── campus-auth/            # 认证服务（登录/注册/JWT）
│   ├── campus-system/          # 系统服务（用户/角色/菜单）
│   ├── campus-common/          # 公共模块（Core/Security/DB/Excel/Log/Redis/Swagger）
│   └── sql/                    # 数据库初始化 & 增量脚本
│
├── campus-frontend/            # Vue3 管理端 (TypeScript)
│   └── src/
│       ├── api/                # 接口层
│       ├── views/              # 页面（home/login/knowledge/system）
│       ├── layout/             # 布局组件
│       ├── stores/             # Pinia 状态
│       └── utils/              # SSE 工具 / Auth 工具
│
├── knowledge_docs/             # 原始校园知识文档 (1,000+ 篇)
├── docs/                       # 项目文档（架构/API/评测/答辩）
├── scripts/                    # 启动/运维脚本
└── pyproject.toml              # Python 项目元数据
```

---

## 🔧 常用命令

```bash
# ---- Python RAG ----
# 启动（开发模式）
uv run --no-sync uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

# 数据库迁移
uv run --no-sync alembic upgrade head            # 执行迁移
uv run --no-sync alembic revision --autogenerate -m "描述"  # 生成迁移

# 重建索引（更新知识库后）
uv run --no-sync python -m app.cli index knowledge_docs --admin-email admin@campusqa.cn

# 运行测试
uv run --no-sync pytest backend/tests/ -v

# ---- Spring Boot ----
# 各服务编译
mvn clean install -DskipTests

# 单独启动某个服务
mvn spring-boot:run -pl campus-system

# ---- Vue 前端 ----
npm run dev          # 开发模式（HMR）
npm run build        # 生产构建
npm run preview      # 预览生产构建
```

### 切换联网搜索引擎

在项目根目录 `.env` 中配置：

```env
# 免费 DuckDuckGo（默认，需代理）
WEB_SEARCH_PROVIDER=free
DDGS_PROXY=http://127.0.0.1:7897

# 百度千帆 AI Search（国内直连，每天免费 100 次）
WEB_SEARCH_PROVIDER=baidu
BAIDU_SEARCH_API_KEY=your-bce-api-key
BAIDU_SEARCH_SECRET_KEY=your-bce-secret-key
```

修改后重启 uvicorn 生效。

---

## 🐛 已知问题 & 排障

<details>
<summary><b>Python 启动报 HF_HUB_OFFLINE 错误</b></summary>

BGE 模型加载时会尝试联网校验版本。启动前务必设置：
```cmd
set HF_HUB_OFFLINE=1
```
如果首次下载模型还需设置镜像：
```cmd
set HF_ENDPOINT=https://hf-mirror.com
```
</details>

<details>
<summary><b>登录成功但接口返回 token 无效</b></summary>

检查所有服务的 `application.yml` 是否包含 `token-prefix: Bearer`。前端发的是 `Authorization: Bearer eyJ...`，缺少这个配置 Sa-Token 会把 `Bearer ` 前缀一起当 token 解析。
</details>

<details>
<summary><b>联网搜索不生效</b></summary>

1. 确认 DuckDuckGo 代理通不通：`curl -m 15 -x http://127.0.0.1:7897 https://duckduckgo.com`
2. 免费搜索仅对"河海大学相关"问题触发，校外问题直接拒答不联网
</details>

<details>
<summary><b>Windows 下 curl/Git Bash 发中文 JSON 乱码</b></summary>

Git Bash 对中文会做 GBK 编码转换。改用 `printf > file` + `--data-binary @file` 发送。
</details>

<details>
<summary><b>验证码登录如何自动化测试</b></summary>

```bash
# 获取验证码 uuid
curl -s http://localhost:19280/auth/captcha | jq -r '.uuid'

# Redis 取验证码值（Python 一行）
uv run python -c "import redis; r=redis.Redis(host='localhost',port=6379,password='your-redis-password'); print(r.get('captcha:<uuid>'))"
```
</details>

---

## 📄 许可证

MIT © 2026 CampusQA Team

---

<div align="center">

**如果这个项目帮到了你，请给一颗 ⭐ Star**

[![Star History Chart](https://api.star-history.com/svg?repos=Wang-Ruibin/RAG&type=Date)](https://star-history.com/#Wang-Ruibin/RAG&Date)

</div>
