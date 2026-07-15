# CampusQA - 河海大学校园知识问答助手

基于 LLM + RAG / Agent + RAG 构建的河海大学校园知识问答系统。

## knowledge_docs 目录说明

知识文档库，存放用于 RAG 检索的河海大学相关知识文档。

| 文件夹 | 内容 | 文档数 |
|--------|------|--------|
| `news/` | 学校新闻、学术动态、科研成果、通知公告 | 198 |
| `academic/` | 教务处通知、研究生院、课程安排、教学工作 | 57 |
| `academic_files/` | 从 PDF/XLSX/PPTX 提取的课程清单、校历、使用指南等 | 16 |
| `university_info/` | 学校概况、院系设置、职能部门、校园文化 | 17 |
| `departments/` | 各学院简介、师资队伍、科研介绍 | 14 |
| `admin/` | 职能部门（资产处、基建处、审计处等） | 13 |
| `alumni/` | 校友会、教育发展基金会、捐赠项目 | 12 |
| `third_party/` | 百度百科、维基百科、教育部、人民网等第三方来源 | 11 |
| `research/` | 科技处、社科处等科研平台信息 | 1 |
| `campus_life/` | 学生工作部等校园生活信息 | 1 |

**来源**：河海大学主站 (hhu.edu.cn) 及各子域名、16个学院官网、12个职能部门网站、百度百科、维基百科、教育部等。每篇文档均标注了网页来源 URL。

## 参考文件

`campus_assistant_arch.md` — 来自其他项目的校园问答助手架构设计文档，作为本项目的参考。其中的技术栈选型（FastAPI + LangChain + ChromaDB）、分层架构设计、多源路由策略等思路可供借鉴。

---

## 后端服务 (Nanoda 分支 · 2026-07-15)

> 贡献者：**Nanoda**  
> Day 1 交付：MySQL 数据库后端信息存储 + 用户问答缓存

### 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| Web 框架 | FastAPI | 异步高性能，自动 Swagger 文档 |
| ORM | SQLAlchemy 2.0 | 声明式模型，pymysql 驱动 |
| 数据库 | MySQL 8.0 | 关系型持久存储 |
| 缓存 | Redis 5.0 | 问答缓存、会话缓存、热数据统计 |
| 认证 | JWT (HS256) | 24h 有效期，角色权限控制 |
| 密码加密 | BCrypt | passlib 实现 |

### 数据库设计

**sys_user** — 用户表
| 字段 | 说明 |
|------|------|
| username | 用户名（唯一索引） |
| password_hash | BCrypt 加密密码 |
| role | 角色：student / teacher / admin |
| status | 1=启用，0=禁用（软删除） |

**kb_document** — 知识库文档表
| 字段 | 说明 |
|------|------|
| title / content | 文档标题与内容 |
| category | 分类：news / academic / departments 等 |
| source_url | 来源 URL |
| status | 0=草稿，1=已发布，2=已归档 |

**qa_record** — 问答记录表
| 字段 | 说明 |
|------|------|
| user_id | 关联用户 (FK) |
| session_id | 会话分组 |
| question / answer | 问题与 AI 回答 |
| sources | 引用来源 JSON |
| feedback | 0=无，1=有用，2=无用 |
| duration_ms | 响应耗时 |

### API 端点（18个）

**用户模块** `/api/user/*`
- `POST /register` — 注册（BCrypt 加密）
- `POST /login` — 登录（返回 JWT）
- `GET /profile` — 个人信息（需认证）
- `PUT /profile` — 更新信息
- `GET /list` — 用户列表（管理员）

**文档模块** `/api/document/*`
- `POST /` — 创建文档
- `GET /list` — 列表（分页 + 分类/部门筛选）
- `GET /categories` — 分类列表
- `GET /{id}` — 详情
- `PUT /{id}` — 更新
- `DELETE /{id}` — 软删除

**问答模块** `/api/qa/*`
- `POST /ask` — 提交问题（缓存优先）
- `POST /answer` — 保存回答 + 写入缓存
- `GET /history` — 会话列表（按 session_id 分组）
- `GET /session/{id}` — 会话详情
- `DELETE /session/{id}` — 删除会话
- `GET /hot` — 热门问题 Top10
- `POST /feedback` — 提交反馈

### 缓存设计

```
campus:qa:qa:{user_id}:{md5(question)}  → 问答缓存（TTL 10min）
campus:qa:session:{session_id}          → 会话历史（TTL 7天）
campus:qa:hot:questions                 → 热门排行（ZSet）
```

Redis 不可用时自动降级到 **fakeredis**（内存模拟），零代码改动。

### 管理员缓存控制台

> `GET /admin/cache` · 需 admin 角色

可视化缓存管理面板，**每 5 秒自动轮询 Redis**，实时反映缓存状态。

| 功能 | 说明 |
|------|------|
| 📊 统计卡片 | 总 Keys、Q&A 缓存、会话缓存、内存占用 · 命中率 |
| 🥧 饼图 | CSS conic-gradient 展示缓存类别分布 |
| 📋 Key 列表 | 按前缀搜索、显示类型和 TTL |
| 🧹 一键清空 | 全部 / 仅 Q&A / 仅会话 / 重置热门 |
| 🔥 缓存预热 | 批量加载热点问题到 Redis |
| 🔄 自动刷新 | 5s 间隔轮询，有人提问面板立即可见 |

**管理员 API** `/api/admin/*`（均需 admin JWT）：

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/cache/stats` | 缓存统计（Keys、内存、命中率、Redis 版本） |
| GET | `/cache/keys` | Key 列表（支持 pattern 筛选） |
| DELETE | `/cache/clear` | 清空全部缓存 |
| DELETE | `/cache/clear/qa` | 清空 Q&A 缓存 |
| DELETE | `/cache/clear/sessions` | 清空会话缓存 |
| DELETE | `/cache/clear/hot` | 重置热门问题 |
| POST | `/cache/warmup` | 缓存预热 |

### 项目结构

```
backend/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置中心
│   ├── database.py          # SQLAlchemy 引擎
│   ├── redis_client.py      # Redis（自动降级到 fakeredis）
│   ├── models/              # ORM 模型（3张表）
│   ├── schemas/             # Pydantic 请求/响应
│   ├── services/            # 业务逻辑
│   ├── routers/             # API 路由（18个端点）
│   └── cache/               # Redis 缓存层
├── init_db.sql              # 建库建表脚本
├── requirements.txt
└── .env
```

### 本地启动

```bash
# 1. 安装依赖
cd backend
pip install -r requirements.txt

# 2. 初始化数据库（MySQL 需已启动）
mysql -u root -p < init_db.sql

# 3. 启动服务
python -m uvicorn app.main:app --reload --port 8002

# 4. 访问 Swagger 文档
# http://localhost:8002/docs
```

### 验证结果 (2026-07-15)

```
✅ 用户注册  → 200  BCrypt 加密存储
✅ JWT 登录  → 200  24h 有效期
✅ 文档 CRUD → 200  分页 + 分类筛选
✅ 问答缓存  → 200  命中 real Redis
✅ 热门问题  → 200  ZSet 排序
```
