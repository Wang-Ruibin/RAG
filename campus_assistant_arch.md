# CampusQA — 校园知识问答助手

<div align="center">
  <img src="https://img.shields.io/badge/python-v3.12.4-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.115-teal.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/LangChain-0.3-orange.svg" alt="LangChain">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
</div>

基于 **FastAPI + LangChain + RAG** 构建的校园知识问答助手，以现有 RAG NoteBook 为底层引擎，面向高校场景提供**课程知识问答、校园信息检索、规章制度查询、智能问答助手**等能力，解决"校园信息分散、课程资料难找、办事流程不清"的问题。

---

## 设计原则

| 原则 | 说明 |
|------|------|
| **增量扩展** | 不重写底层，在现有 RAG 引擎、Agent 编排、ChromaDB 向量存储之上叠加校园领域层 |
| **多源路由** | 查询先做意图分类，再路由到对应知识源（课程/校园/制度/FAQ），而非单一检索 |
| **用户隔离** | 学生/教师/管理员多角色，知识库按角色+组织双向隔离 |
| **时效感知** | 课程按学期、制度按版本、校历按时间，所有检索结果携带时效标签 |

---

## 核心特性

- **🏫 校园知识问答**：校园概况、地理位置、部门信息、历史沿革等综合问答
- **📚 课程资料问答**：上传 syllabus / PPT / 教材，按课程隔离，章节级精准检索
- **📋 规章制度查询**：学生手册、教务规定、宿舍管理等，按部门+版本检索
- **❓ 高频 FAQ 匹配**：精确 + 语义双通道匹配，秒回常见问题
- **🧭 办事流程指引**：请假、选课、奖学金申请等流程分步指引
- **📅 校历与日程**：学期安排、考试时间、节假日查询
- **🎯 课程推荐**：基于兴趣关键词语义匹配课程
- **🔐 多角色权限**：学生 / 教师 / 管理员，数据按角色+学院隔离
- **💬 持久化对话**：会话历史存储 MySQL，随时回溯上下文

---

## 项目架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          接入层 Access Layer                         │
│                                                                     │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│   │  Web 端 (Vue 3) │  │  移动端 (适配)   │  │  第三方 API 接入  │    │
│   └────────┬────────┘  └────────┬────────┘  └────────┬────────┘    │
│            └────────────────────┼────────────────────┘              │
│                                 ▼                                   │
│                     JWT 认证 + 角色鉴权                              │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                     编排层 Orchestration Layer                       │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                    CampusAgent (主 Agent)                     │   │
│   │  继承现有 AgentFactory，注入校园工具集 + 校园系统提示词          │   │
│   └──────────┬────────────────────────────────────────┬──────────┘   │
│              │ 意图分类                                │ 工具调用     │
│              ▼                                        ▼              │
│   ┌──────────────────┐              ┌────────────────────────────┐   │
│   │  QueryAnalyzer   │              │     Campus Tool Registry   │   │
│   │  (LLM 意图分类)   │              │  ┌──────────────────────┐ │   │
│   │                  │              │  │campus_info / course_qa│ │   │
│   │ 输出: IntentType │──────────────▶│  │policy / calendar     │ │   │
│   └──────────────────┘              │  │recommend / faq       │ │   │
│                                      │  │document_flow         │ │   │
│                                      │  └──────────────────────┘ │   │
│                                      └────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                      路由层 Routing Layer                             │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                     CampusRouter                              │   │
│   │                                                               │   │
│   │   query ──▶ intent classify ──▶ select collections ──▶ retrieve│   │
│   │                                                               │   │
│   │   意图 → 知识源映射表：                                        │   │
│   │   ┌─────────────────┬──────────────────────────────────┐      │   │
│   │   │ 校园信息         │ campus_info_collection            │      │   │
│   │   │ 课程知识         │ course_{id}_collection + 笔记库    │      │   │
│   │   │ 规章制度         │ policy_collection                 │      │   │
│   │   │ 办事流程         │ flow_collection + FAQ 表          │      │   │
│   │   │ 校园资讯         │ news_collection                   │      │   │
│   │   │ 高频问答         │ FAQ 精确匹配 + 模糊语义匹配         │      │   │
│   │   │ 综合类           │ 多集合并行检索 + 统一重排序        │      │   │
│   │   └─────────────────┴──────────────────────────────────┘      │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │  组合检索 CompositeRetriever (复用 HybridRetriever)           │   │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │   │
│   │  │BM25 检索  │  │向量检索   │  │权重调整  │  │结果合并  │    │   │
│   │  │(关键词)   │  │(语义)    │  │(动态)   │  │+ 去重   │    │   │
│   │  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │   │
│   └─────────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                      增强层 Enhancement Layer                         │
│                                                                     │
│   ┌───────────────────┐  ┌───────────────────┐  ┌────────────────┐  │
│   │ ReorderService    │  │  SliceSummarizer   │  │  ContextMerge  │  │
│   │ (CrossEncoder     │  │  (分片并行总结)     │  │  (多源结果融合) │  │
│   │  重排序)           │  │                    │  │                │  │
│   └───────────────────┘  └───────────────────┘  └────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                       数据层 Data Layer                               │
│                                                                     │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│   │  MySQL   │  │  Redis   │  │ ChromaDB │  │   文件存储        │   │
│   │          │  │          │  │          │  │                  │   │
│   │• 会话     │  │• JWT缓存 │  │• campus  │  │• 课程资料 PDF    │   │
│   │• 用户     │  │• FAQ缓存 │  │  _info   │  │• 制度文档        │   │
│   │• 课程     │  │• 校历    │  │• course  │  │• 校园地图/图片   │   │
│   │• 文档元   │  │  缓存   │  │  _合集    │  │                  │   │
│   │  数据     │  │         │  │• policy  │  │                  │   │
│   │• FAQ 表  │  │         │  │• news    │  │                  │   │
│   └──────────┘  └──────────┘  └──────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 数据模型设计

在现有 ORM 模型基础上增量扩展：

### 校园文档

```python
class CampusDocument(Base):
    """校园知识库文档 — 校园概况 / 规章制度 / 办事流程 / 校园资讯"""
    __tablename__ = "campus_documents"

    id: int (PK, auto)
    title: str                   # 文档标题
    content: text                # 文档内容 (Markdown)
    category: str                # 分类: campus_info / policy / flow / news / general
    department: str | null       # 所属部门 (如: 教务处 / 学生处 / 后勤)
    tags: JSON                   # 标签数组
    valid_from: date | null      # 生效日期 (制度版本管理)
    valid_until: date | null     # 失效日期
    is_active: bool = True       # 是否启用
    view_count: int = 0          # 访问次数
    created_at: datetime
    updated_at: datetime
```

### 课程与课程资料

```python
class Course(Base):
    """课程信息"""
    __tablename__ = "courses"

    id: int (PK, auto)
    code: str (unique)           # 课程代码 (如: CS101)
    name: str                    # 课程名称
    instructor: str              # 授课教师
    department: str              # 开课院系
    semester: str                # 学期 (如: 2026春)
    description: text | null     # 课程简介
    syllabus_path: str | null    # 教学大纲文件路径
    created_at: datetime
    updated_at: datetime

class CourseMaterial(Base):
    """课程资料文件（映射到 Chroma 向量集合）"""
    __tablename__ = "course_materials"

    id: int (PK, auto)
    course_id: int (FK → courses.id, CASCADE)
    title: str
    file_type: str               # pdf / pptx / docx / md
    file_path: str
    chunk_status: str            # pending / processing / ready / failed
    chunk_count: int = 0         # 切片数量
    md5: str                     # 文件去重哈希
    uploaded_by: int             # 上传者 user_id
    created_at: datetime
```

### FAQ 问答对

```python
class FAQ(Base):
    """高频问答对 — 精确匹配 + 模糊语义匹配"""
    __tablename__ = "faq"

    id: int (PK, auto)
    question: str                # 标准问题
    answer: text                 # 标准答案
    category: str | null         # 分类 (如: 教务 / 生活 / 就业)
    tags: JSON                   # 标签
    keywords: JSON               # 关键词数组 (用于精确匹配)
    similar_questions: JSON      # 相似问法 (用于扩展匹配)
    hit_count: int = 0           # 命中次数
    priority: int = 0            # 优先级 (高优先级优先返回)
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
```

---

## 路由设计 (API Endpoints)

### 校园问答路由 `/campus`

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/campus/query` | 校园知识问答（流式/非流式） |
| POST | `/campus/query/direct` | 校园信息直接检索（非 Agent） |
| POST | `/campus/course/{course_id}/qa` | 课程资料问答 |
| POST | `/campus/policy/search` | 规章制度检索 |
| POST | `/campus/faq/match` | FAQ 精确+模糊匹配 |
| GET  | `/campus/faq/hot` | 热门 FAQ 列表 |
| GET  | `/campus/calendar` | 校历查询（按学期） |

### 课程管理路由 `/campus/course`

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/campus/course` | 创建课程 |
| GET  | `/campus/course/list` | 课程列表（分页+筛选） |
| GET  | `/campus/course/{id}` | 课程详情 |
| PUT  | `/campus/course/{id}` | 更新课程 |
| DELETE | `/campus/course/{id}` | 删除课程 |
| POST | `/campus/course/{id}/material` | 上传课程资料 |
| GET  | `/campus/course/{id}/material` | 课程资料列表 |
| DELETE | `/campus/course/{id}/material/{mid}` | 删除课程资料 |
| POST | `/campus/course/{id}/reindex` | 重新索引课程向量库 |

### 校园文档管理路由 `/campus/document`

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/campus/document` | 创建校园文档 |
| GET  | `/campus/document/list` | 文档列表（按分类/部门筛选） |
| GET  | `/campus/document/{id}` | 文档详情 |
| PUT  | `/campus/document/{id}` | 更新文档 |
| DELETE | `/campus/document/{id}` | 删除文档 |
| POST | `/campus/document/batch-import` | 批量导入文档 |
| POST | `/campus/document/{id}/reindex` | 重新索引文档向量 |

### FAQ 管理路由 `/campus/faq`

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/campus/faq` | 创建 FAQ |
| GET  | `/campus/faq/list` | FAQ 列表（分页+筛选） |
| PUT  | `/campus/faq/{id}` | 更新 FAQ |
| DELETE | `/campus/faq/{id}` | 删除 FAQ |
| POST | `/campus/faq/batch-import` | 批量导入 FAQ |

---

## Agent 工具设计

在现有 `app/agent/agent_tools.py` 基础上新增：

| 工具 | 说明 | 数据源 |
|------|------|--------|
| `campus_info_tools(query)` | 校园概况/部门/位置等综合查询 | campus_info Chroma 集合 |
| `course_qa_tool(course_code, query)` | 指定课程资料问答 | course_{id} Chroma 集合 |
| `search_policy_tool(query, dept=None)` | 制度检索（按部门筛选） | policy Chroma 集合 |
| `query_faq_tool(query)` | FAQ 精确+语义匹配 | FAQ 表 + Redis 缓存 |
| `get_calendar_tool(semester=None)` | 校历/考试安排查询 | MySQL |
| `find_office_tool(department)` | 部门/办公室位置查询 | MySQL 结构化数据 |
| `recommend_course_tool(keywords)` | 课程推荐（语义匹配） | courses 表 + 向量嵌入 |
| `document_flow_tool(flow_type)` | 办事流程分步指引 | flow Chroma 集合 |

---

## Prompt 体系

在 `app/prompt/` 中新增：

| 文件 | 用途 |
|------|------|
| `campus_main_prompt.txt` | 校园助手系统提示词 — 角色设定为"校园智能向导"，具备校园知识、耐心友好、引用来源 |
| `campus_router_prompt.txt` | 意图分类 Prompt — 将用户query分类为 campus_info / course_qa / policy / faq / calendar / general |
| `course_qa_prompt.txt` | 课程问答专用 Prompt — 强调引用课程材料原文，超出范围时明确说明 |
| `policy_qa_prompt.txt` | 制度问答 Prompt — 强调版本时效性，标注生效/失效日期 |

---

## 关键技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **Web 框架** | FastAPI | 异步高性能 Web 框架（复用） |
| **AI 编排** | LangChain Agent | 工具调用型 Agent（复用 AgentFactory + AgentExecutor） |
| **向量数据库** | ChromaDB | 多集合隔离（每课程独立 collection）（复用） |
| **混合检索** | BM25 + 向量检索 | HybridRetriever 权重动态调整（复用） |
| **重排序** | CrossEncoder (Qwen3-Reranker) | 精排 Top-K 结果（复用 ReorderService） |
| **关系数据库** | MySQL | 课程/文档/FAQ/会话数据（复用） |
| **缓存** | Redis | FAQ 缓存 / JWT 缓存 / 校历缓存（复用） |
| **LLM** | 阿里云百炼 / Ollama | 大模型推理（复用工厂模式） |
| **嵌入模型** | text-embedding / qwen3-embedding | 向量化（复用） |
| **文档切片** | AsyncTextSplitter | 课程章节感知切片（扩展 CampusTextSplitter） |
| **前端** | Vue 3 + Vant 4 | 移动端友好界面（复用，新增校园模块） |

---

## 项目实施结构

```
backend/
├── app/
│   ├── campus/                          # 【新增】校园问答模块
│   │   ├── __init__.py
│   │   ├── router.py                    # 校园问答 API 路由
│   │   ├── service.py                   # CampusService 业务编排
│   │   ├── campus_agent.py              # CampusAgent (继承 AgentFactory)
│   │   ├── campus_router.py             # CampusRouter 意图分类+知识源路由
│   │   ├── campus_tools.py              # 校园 Agent 工具集 (8个)
│   │   ├── text_splitter.py             # CampusTextSplitter 章节感知分割
│   │   └── models.py                    # Pydantic 请求/响应模型
│   ├── agent/
│   │   └── agent_tools.py               # 【扩展现有】注入校园工具
│   ├── models/
│   │   └── campus.py                    # 【新增】CampusDocument / Course / CourseMaterial / FAQ ORM
│   ├── prompt/
│   │   ├── campus_main_prompt.txt       # 【新增】校园助手系统提示词
│   │   ├── campus_router_prompt.txt     # 【新增】意图分类 Prompt
│   │   ├── course_qa_prompt.txt         # 【新增】课程问答 Prompt
│   │   └── policy_qa_prompt.txt         # 【新增】制度问答 Prompt
│   ├── config/
│   │   └── campus.yaml                  # 【新增】校园模块配置 (集合名/切片参数)
│   ├── rag/
│   │   ├── vector_store.py              # 【扩展】增加多集合管理能力
│   │   └── text_spliter.py              # 【扩展】增加校园章节分割策略
│   └── router/
│       └── campus_router.py             # 【新增】校园管理后台路由
│
front/
├── src/
│   ├── views/
│   │   └── CampusQA.vue                 # 【新增】校园问答页面
│   ├── components/
│   │   └── CourseSelector.vue           # 【新增】课程选择器组件
│   ├── router/
│   │   └── index.js                     # 【扩展】增加校园模块路由
│   └── store/
│       └── campus.js                    # 【新增】校园模块状态管理
```

---

## 实施路线图

### Phase 1：基础问答能力 (2周)

| 任务 | 产出 |
|------|------|
| 创建 CampusDocument / Course / CourseMaterial / FAQ 数据模型 | 4 张 MySQL 表 + Alembic 迁移 |
| 实现 CampusRouter 意图分类 + 多集合路由 | 查询精准路由到对应知识源 |
| 实现 CampusService 业务编排 | 完整的校园问答 API |
| 注册前 4 个核心 Agent 工具 | campus_info / course_qa / policy / faq |
| 编写 4 个校园 Prompt 模板 | 角色设定 + 意图分类 + 领域约束 |
| 前端 CampusQA 页面 | 校园问答聊天界面 |

### Phase 2：课程知识问答 (1周)

| 任务 | 产出 |
|------|------|
| CampusTextSplitter 章节感知分割 | 课程资料按章节/知识点切片 |
| 每课程独立 Chroma 集合 | 课程级数据隔离 |
| 课程资料上传 + 自动索引 | 上传即用，增量更新 |
| CourseSelector 组件 | 前端课程切换 |

### Phase 3：智能增强 (2周)

| 任务 | 产出 |
|------|------|
| 课程推荐工具（语义匹配） | `recommend_course_tool` |
| FAQ 自动发现（对话热门提炼） | 后台定时任务 |
| 制度版本管理与时效提醒 | `valid_from / valid_until` 过滤 |
| 校历与日程集成 | 日历查询 API + 缓存 |
| 多角色鉴权 | 学生/教师/管理员数据隔离 |

---

## 与现有系统的关系

```
┌─────────────────────────────────────────────────────┐
│                  校园知识问答助手                       │
│  ┌──────────────────────────────────────────────┐   │
│  │          增量扩展 (校园专属)                     │   │
│  │  • CampusRouter 意图路由                      │   │
│  │  • CampusTextSplitter 课程分割                │   │
│  │  • 8 个校园 Agent 工具                        │   │
│  │  • 4 张校园数据表 + 多集合 Chroma              │   │
│  └──────────────────┬───────────────────────────┘   │
│                      │ 继承                           │
│  ┌──────────────────▼───────────────────────────┐   │
│  │          RAG NoteBook 核心引擎                  │   │
│  │  • HybridRetriever (BM25 + 向量)              │   │
│  │  • ReorderService (CrossEncoder 重排序)       │   │
│  │  • AgentFactory + AgentExecutor               │   │
│  │  • ChromaDB 单例 + 切片管理                   │   │
│  │  • JWT 认证 + 限流 + 日志                     │   │
│  │  • 多格式文档处理器 (PDF/PPTX/DOCX/MD/TXT)    │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

**关键继承点**：不修改一行现有引擎代码，通过策略扩展（Strategy Pattern）和工具注册（Tool Registry）实现校园特化。现有 RAG NoteBook 的所有功能完全保留，校园模块作为独立插件式扩展运行。
