# CampusQA - 河海大学校园知识问答助手

基于 RAG（检索增强生成）构建的河海大学校园知识问答系统。

## 知识库

`knowledge_docs/` 目录包含 340 篇河海大学相关知识文档，覆盖：

| 文件夹 | 内容 | 文档数 |
|--------|------|--------|
| `news/` | 学校新闻、学术动态、通知公告 | 198 |
| `academic/` | 教务处通知、研究生院、课程安排 | 57 |
| `university_info/` | 学校概况、院系设置、校园文化 | 17 |
| `academic_files/` | 课程清单、校历、使用指南 | 16 |
| `departments/` | 各学院简介、师资队伍 | 14 |
| `admin/` | 职能部门信息 | 13 |
| `alumni/` | 校友会、教育发展基金会 | 12 |
| `third_party/` | 百度百科、维基百科、教育部等 | 11 |
| `research/` | 科研平台信息 | 1 |
| `campus_life/` | 校园生活 | 1 |

---

## 功能介绍

### 智能问答

- 支持 **RAG 模式**（默认开启）：检索知识库后由 AI 生成回答，每条可核查事实标注引用来源  
- 回答附带**来源卡片**：展示相关度评分、原文片段、来源链接、发布日期
- **低置信拒答**：知识库外的问题自动回复「未找到相关信息」，避免生成幻觉
- **闲聊识别**：问候/寒暄自动跳过检索，直接返回引导信息
- **会话持久化**：问答记录自动保存，切换页面不丢失，左侧栏可查看历史会话
- **流式打字机**：SSE 逐字显示，发送中显示 loading，支持「停止生成」
- **多轮对话**：自动携带最近 6 轮历史上下文，解决指代消解

### 知识库文档管理

- 支持**上传 .txt/.pdf/.doc/.docx 文档**，填写标题、分类、来源链接
- 文档列表支持分类筛选、关键词搜索
- **重建索引按钮**：一键清空向量库 → 将列表中全部文档重新向量化 → 即时生效
- 删除文档同步清理对应向量

### 用户系统

- 注册 / 登录（JWT + BCrypt）
- **修改密码**：个人中心可直接修改密码
- 管理员：用户管理（角色切换、启禁用）、硬删除用户（彻底从 MySQL 移除）

### 缓存系统

- Redis 问答缓存 + 会话缓存 + 热门问题排行
- Redis 不可用时自动降级到内存模式
- 管理员可视化缓存面板：实时统计、Key 搜索、一键清空、缓存预热

### 评测框架

- 50 条评测数据集（单轮知识题 + 多轮对话 + 知识库外问题）
- 支持多种检索配置对比：dense-only / hybrid / hybrid+reranker
- 指标：Hit@5、MRR@5、Precision、Recall、OOD 拒答率、P95 延迟

---

## 技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | FastAPI |
| 数据库 | MySQL 8.0 + SQLAlchemy |
| 缓存 | Redis 5.0（自动降级 fakeredis） |
| 认证 | JWT (HS256) + BCrypt |
| 嵌入模型 | BAAI/bge-small-zh-v1.5 (512 维) |
| 向量库 | FAISS (IndexFlatIP) |
| 关键词检索 | BM25Okapi (jieba 分词) |
| 融合 | RRF (Reciprocal Rank Fusion, k=60) |
| 重排序 | BGE-reranker-base（可选开关） |
| 生成模型 | DeepSeek API (deepseek-chat) |
| 前端 | React 18 + TypeScript + Vite + Ant Design + Tailwind CSS |

---

## 项目结构

```
├── ai_service/               # AI 微服务 (port 8003)
│   ├── main.py               # FastAPI: /query, /stream, /reindex, /rebuild, /stats
│   ├── config.py             # Pydantic 配置中心
│   ├── engine/
│   │   ├── pipeline.py       # RAG 管线编排
│   │   ├── retriever.py      # FAISS 稠密检索 + 低置信检测
│   │   ├── embedding.py      # BGE 嵌入（懒加载单例）
│   │   ├── chunker.py        # 文档切片
│   │   ├── loader.py         # 知识文档加载
│   │   ├── vector_store.py   # FAISS 索引管理
│   │   ├── bm25_retriever.py # BM25 关键词检索（jieba）
│   │   ├── fusion.py         # RRF 融合
│   │   ├── reranker.py       # Cross-Encoder 重排
│   │   ├── citation.py       # 引用后校验
│   │   ├── artifact_store.py # 单文档工件存储
│   │   ├── generator.py      # DeepSeek API 客户端
│   │   └── prompts.py        # Prompt 模板
│   ├── data/                 # FAISS 索引 + 工件 + BM25
│   └── cli.py                # 命令行工具
│
├── backend/                  # 业务后端 (port 8002)
│   ├── app/
│   │   ├── main.py           # FastAPI 入口
│   │   ├── config.py         # 配置中心
│   │   ├── database.py       # SQLAlchemy 引擎
│   │   ├── redis_client.py   # Redis（降级 fakeredis）
│   │   ├── models/           # ORM 模型
│   │   ├── schemas/          # Pydantic 请求/响应
│   │   ├── services/         # 业务逻辑
│   │   ├── routers/          # API 路由
│   │   └── cache/            # Redis 缓存层
│   ├── alembic/              # 数据库迁移
│   ├── tests/                # pytest 测试（184 个）
│   └── init_db.sql           # 建库脚本
│
├── frontend/                 # React 前端
│   └── src/
│       ├── pages/            # Chat, Documents, Profile, Login, Admin, UserManagement
│       ├── components/       # SourceCards, Layout
│       ├── context/          # AuthContext
│       ├── lib/              # SSE 客户端
│       └── services/         # API 客户端
│
├── evals/                    # 评测框架 + 数据集 + 报告
├── start.ps1                 # 一键启动脚本
└── start.bat                 # Windows 快捷启动
```

---

## API 端点

### AI 服务 (port 8003)

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/query` | 同步 RAG 问答 |
| GET | `/query/stream` | SSE 流式问答 |
| POST | `/rebuild` | 清空并重建全部索引 |
| GET | `/reindex` | 从 knowledge_docs/ 全量重建 |
| POST | `/process` | 处理单篇文档文件 |
| DELETE | `/document/{id}` | 删除文档向量 + 工件 |
| GET | `/stats` | 知识库统计 |
| GET | `/health` | 健康检查 |

### 业务后端 (port 8002)

| 模块 | 端点 | 说明 |
|------|------|------|
| 用户 | `POST /api/user/register` | 注册 |
| | `POST /api/user/login` | 登录 |
| | `GET/PUT /api/user/profile` | 个人信息 |
| | `PUT /api/user/change-password` | 修改密码 |
| | `GET /api/user/list` | 用户列表（管理员，默认仅活跃用户） |
| | `DELETE /api/user/{id}` | 硬删除用户 |
| | `PUT /api/user/{id}/status` | 启用/禁用用户 |
| 文档 | `POST /api/document` | 创建文档（自动触发索引） |
| | `GET /api/document/list` | 文档列表（分页+筛选） |
| | `PUT /api/document/{id}` | 更新文档 |
| | `DELETE /api/document/{id}` | 删除文档 + 向量 |
| | `POST /api/document/rebuild-index` | 重建索引（管理员） |
| 问答 | `POST /api/qa/ask` | 提交问题 |
| | `GET /api/qa/history` | 会话列表 |
| | `GET /api/qa/session/{id}` | 会话详情 |
| | `GET /api/qa/hot` | 热门问题 |
| | `POST /api/qa/feedback` | 提交反馈 |
| AI | `POST /api/ai/query` | RAG 问答代理 |
| | `GET /api/ai/query/stream` | SSE 流式问答（带 history 参数） |

---

## 本地启动

### 前提

- Python 3.11、Node.js、MySQL 8.0、Redis 5.0（可选）

### 一键启动（Windows）

```powershell
# 确保代理开启（如需访问外网 API）
. $PROFILE; proxy on

# 双击或运行
.\start.bat
```

启动后自动打开浏览器，访问 `http://localhost:8002`。

### 手动启动

```bash
# 1. AI 服务 (port 8003)
cd ai_service
pip install -r requirements.txt
python -m uvicorn main:app --port 8003

# 2. 业务后端 (port 8002)
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8002

# 3. 前端
cd frontend
npm install
npm run dev
```

### 首次使用

1. 注册账号 → 登录
2. 进入「知识库文档」→ 上传几篇 .txt 文档 → 点击「重建索引」
3. 进入「智能问答」→ 开始提问

### 运行测试

```bash
# 后端测试（不含模型加载）
cd backend
python -m pytest tests/ --ignore=tests/test_reranker.py

# 前端测试
cd frontend
npx vitest run
```

---

## PPT 课程对照

| Day | 主题 | 要求 | 完成 |
|-----|------|------|------|
| Day1 | 前置与环境搭建 | GitHub、环境、数据库 | ✅ |
| Day2 | 基础功能开发 | 注册登录 JWT、CRUD | ✅ |
| Day3 | RAG 技术专题 | 切分、Embedding、FAISS | ✅ |
| Day4 | 业务模块开发 | 文档上传、处理流转 | ✅ |
| Day5 | AI 模块开发 | RAG 问答、SSE 流式、多轮 | ✅ |
| Day6 | 测试与发布 | 测试、打包、文档 | ✅ |

> 技术栈：PPT 要求 Java/Spring Boot，本项目使用 Python/FastAPI，功能完全等价。
