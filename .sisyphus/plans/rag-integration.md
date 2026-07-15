# RAG 集成 — 校园知识问答助手

## TL;DR

> **目标**：将 340 篇河海大学知识文档 RAG 化，接入现有后端，让 AI 基于文档语义检索回答问题
>
> **核心交付**：独立 ai_service 微服务（端口 8003）+ 文档切分 → Embedding → FAISS → TopK → Prompt → DeepSeek → SSE 流式 → 引用来源
>
> **范围**：Wave 1~5（~16 个 Todo，5 个并行 Wave）
> **砍掉项**：Reranker (1.1GB)、BM25 混合检索、通义千问 fallback
> **包含项**：✅ SSE 流式输出（用户要求现在做）
> **并行策略**：YES - 5 个 Wave

---

## Context

### 现状
- **FastAPI 后端**（端口 8002）：用户/文档/问答/管理四组路由 + MySQL + Redis
- **React 前端**：Chat/Documents/UserManagement/Admin 四个页面
- **知识文档**：`knowledge_docs/` 下 **340 个 .md** 文件（不是 README 写的 299），10 个子目录
- **参考代码**：`rag_hhu/rag_hhu.py` — TF-IDF + DeepSeek 的最小 RAG 脚本
- **已有 API Key**：`rag_hhu/.env` 中 DeepSeek `sk-6c8e...a831`
- **前端 Chat.tsx** 已有 `sources` 字段和 `Message` 接口，可直接对接 RAG

### 已知问题（Metis 发现）
- 340 个 .md 中有重复标题、HTML 导航残留（`上一篇：下一篇：`）、空标题
- 文件名含中文特殊字符（《》、空格），Windows pathlib 需测试
- Python 3.11 兼容性需验证（sentence-transformers, faiss-cpu）

### PPT 要求映射

| PPT 要求 | 计划实现 | 优先级 |
|----------|----------|:------:|
| 文档切分（chunk_size=500, overlap=50） | ✅ RecursiveCharacterTextSplitter | P0 |
| Embedding 向量化 | ✅ BGE-small-zh-v1.5 | P0 |
| FAISS 向量库 | ✅ IndexFlatIP | P0 |
| TopK 检索 | ✅ TopK=5，可配置 | P0 |
| Prompt 拼接 | ✅ context + question + 系统指令 | P0 |
| LLM 调用 | ✅ DeepSeek API | P0 |
| 答案引用来源 | ✅ 返回来源文档+相似度 | P0 |
| CLI 可运行脚本 | ✅ cli.py（Day3 必须） | P1 |
| 参数对比测试 | ✅ benchmark.py | P1 |
| 文档上传+处理 | ✅ POST /api/ai/process | P1 |
| React 引用展示 | ✅ Chat 页面显示来源 | P2 |
| 流式输出 SSE | ✅ sse-starlette 逐 token 流式 | P1 |
| 重排序 Rerank | ❌ 砍掉（1.1GB） | — |
| 混合检索 BM25 | ❌ 砍掉（340 条不需要） | — |
| 通义千问 fallback | ❌ 砍掉 | — |

---

## Work Objectives

### 核心目标
将 knowledge_docs/ 知识库通过 RAG 流程接入系统，使问答助手能基于文档内容回答用户问题，并标注引用来源。

### 具体交付物
- 后端 RAG 引擎（`backend/app/rag/`）+ 编排层 + 路由
- CLI 独立脚本（`ai_service/cli.py`）
- 参数对比测试（`ai_service/benchmark.py`）
- 前端 Chat 显示引用来源
- 文档上传+处理流程

### Must Have
- RAG 流程完整可跑通：loader → chunker → embedding → FAISS → retriever → prompt → generate
- 回答必须基于文档内容（验证：问校训返回"艰苦朴素、实事求是、严格要求、勇于探索"）
- 回答附带引用来源（文档标题 + 片段预览 + 相似度分数）
- CLI 脚本可独立运行（`python cli.py --ask "校训是什么？"`）
- 文档上传后自动触发处理（切分→向量化→入库）

### Must NOT Have
- 不修改现有 API 响应格式 `{code, message, data, timestamp}`
- 不修改现有 `/api/user`, `/api/document`, `/api/qa` 路由
- 不修改 MySQL 现有三张表结构
- 不引入 1.1GB 以上的模型（bge-reranker-base）
- 不修改前端/login、/profile 等现有页面

---

## Verification Strategy

### 测试决策
- **自动化测试**：无（项目无测试框架）
- **CLI 测试**：`python cli.py --test` 验证 10 道预定义题（复用 rag_hhu 测试集）
- **API 测试**：`curl POST /api/ai/query` 验证返回格式

### Agent QA 策略
- 每个 Todo 执行后，执行验证命令输出结果
- CLI 测试全部 PASS（10/10）视为通过
- API 返回格式验证：contains `answer` + `sources` 字段
- **不依赖人工目测**，用命令 + grep 验证

---

## Execution Strategy

### Wave Plan

```
Wave 1 — RAG 引擎基础（并行5组件，无依赖）
├── T1: 项目骨架 + 依赖安装
├── T2: 文档加载器 Loader
├── T3: 文档切分器 Chunker
├── T4: 嵌入服务 Embedding
└── T5: FAISS 向量库 VectorStore

Wave 2 — 检索与生成（依赖 Wave 1）
├── T6: 检索器 Retriever（纯FAISS TopK）
├── T7: LLM 生成器 Generator（DeepSeek）
├── T8: Prompt 模板系统
└── T9: RAG 流水线 Pipeline

Wave 3 — 后端集成（依赖 Wave 2）
├── T10: RAG 编排层 rag_service
├── T11: AI 路由 ai.py（query + process + stats）
├── T12: 文档上传改进（PDF/Word/TXT）
└── T13: CLI 独立脚本 cli.py

Wave 4 — 前端（依赖 Wave 3）
├── T14: Chat 引用来源展示
└── T15: 文档上传 UI + 状态展示

Wave 5 — 测试与收尾（依赖 Wave 4）
├── T16: 参数对比测试 benchmark.py
├── T17: 全链路验证测试
├── F1: README 更新
└── F2: 代码审查 + 提交

总 Todo: ~17 个，5 个 Wave
```

---

## TODOs

### Wave 1 — RAG 引擎基础 (5 Tasks, 可并行)

- [ ] 1. **项目骨架 + 依赖安装**

  **What to do**:
  - 在 `backend/` 下创建 `app/rag/` 目录结构
  - 安装依赖：`sentence-transformers`, `faiss-cpu`, `langchain`, `rank-bm25`, `jieba`, `numpy`, `openai`
  - 验证 Python 3.11 兼容性：`import sentence_transformers` 不报错
  - 从 `rag_hhu/.env` 复制 DEEPSEEK_API_KEY 到 `backend/.env`
  - 创建 `app/rag/__init__.py`

  **Recommended Agent Profile**: `quick`
  **Parallelization**: Wave 1 (with T2-T5)
  **Blocks**: T6-T9

  **Acceptance Criteria**:
  - `pip install` 完成无报错
  - `python -c "import sentence_transformers; import faiss; import langchain"` 通过

  **QA Scenarios**:
  ```
  Scenario: 依赖安装验证
    Tool: Bash
    Steps:
      1. pip install sentence-transformers faiss-cpu langchain
      2. python -c "import sentence_transformers; import faiss; from langchain.text_splitter import RecursiveCharacterTextSplitter; print('OK')"
    Expected: 输出 "OK"
    Evidence: .sisyphus/evidence/t01-deps.txt
  ```

- [ ] 2. **文档加载器 Loader**

  **What to do**:
  - 读取 `knowledge_docs/` 下所有 `.md` 文件
  - 过滤规则：跳过 `< 50` 字符的无效文件
  - 提取内容：文件内容（去除 HTML 导航残留 `上一篇：`、`下一篇：`）
  - 提取元数据：`doc_id`(文件路径hash)、`title`(文件名)、`category`(子目录名)、`source_url`(如有)
  - 支持单文件加载和批量加载两种模式
  - 先验证 5 个文件，再扩展到全部 340 个

  **Recommended Agent Profile**: `unspecified-high`
  **Parallelization**: Wave 1 (with T1, T3-T5)
  **Blocks**: T6
  **References**: `rag_hhu/rag_hhu.py` 爬虫的文本清理逻辑

  **Acceptance Criteria**:
  - 加载 5 个测试文件成功返回 `[{doc_id, title, content, category}]`
  - 340 个文件全部加载无异常

  **QA Scenarios**:
  ```
  Scenario: 批量加载验证
    Tool: Bash
    Steps:
      1. cd backend && python -c "from app.rag.loader import load_knowledge_docs; docs=load_knowledge_docs(); print(len(docs))"
    Expected: 输出 "340"
    Evidence: .sisyphus/evidence/t02-loader.txt
  ```

- [ ] 3. **文档切分器 Chunker**

  **What to do**:
  - 使用 `langchain.text_splitter.RecursiveCharacterTextSplitter`
  - 参数：`chunk_size=500`, `chunk_overlap=50`
  - 中文按句号/换行符优先切分
  - 输出格式：`[{content, doc_id, chunk_index, title, category}]`
  - 统计切分结果：总 chunk 数、平均 chunk 长度

  **Recommended Agent Profile**: `unspecified-high`
  **Parallelization**: Wave 1 (with T1-T2, T4-T5)
  **Blocks**: T6

  **Acceptance Criteria**:
  - 340 个文档切分完成后总 chunk 数正常（预计 ~2000-3000 块）

  **QA Scenarios**:
  ```
  Scenario: 切分验证
    Tool: Bash
    Steps:
      1. cd backend && python -c "from app.rag.chunker import chunk_docs; from app.rag.loader import load_knowledge_docs; docs=load_knowledge_docs(); chunks=chunk_docs(docs); print('chunks:', len(chunks)); print('avg_len:', sum(len(c['content']) for c in chunks)//len(chunks))"
    Expected: chunks > 1000
    Evidence: .sisyphus/evidence/t03-chunker.txt
  ```

- [ ] 4. **嵌入服务 Embedding**

  **What to do**:
  - 使用 `sentence_transformers.SentenceTransformer('BAAI/bge-small-zh-v1.5')`
  - 向量维度：384
  - 归一化：`normalize_embeddings=True`
  - 批量编码：batch_size=32
  - 设备：CPU（Windows 兼容）
  - `device='cpu'` 强制指定避免 CUDA 问题
  - 模型缓存：默认 `~/.cache/huggingface/`

  **Recommended Agent Profile**: `unspecified-high`
  **Parallelization**: Wave 1 (with T1-T3, T5)
  **Blocks**: T6

  **Acceptance Criteria**:
  - 模型加载成功（首次下载 ~12MB）
  - 1 个文本返回 384 维向量
  - 32 个文本 batch 编码不报错

  **QA Scenarios**:
  ```
  Scenario: 嵌入服务验证
    Tool: Bash
    Steps:
      1. cd backend && python -c "from app.rag.embedding import embed; vecs=embed(['河海大学校训是什么']); print('shape:', len(vecs[0]))"
    Expected: shape: 384
    Evidence: .sisyphus/evidence/t04-embedding.txt
  ```

- [ ] 5. **FAISS 向量库 VectorStore**

  **What to do**:
  - 使用 `faiss.IndexFlatIP`（内积相似度）
  - 元数据存储：另存 JSON 文件，下标与 FAISS 对齐
  - 方法：
    - `build(vectors, metadata)` — 从零建库
    - `add(vectors, metadata)` — 追加
    - `search(query_vector, top_k=5)` — 返回 `[{content, score, doc_id, title, chunk_index}]`
    - `delete(doc_id)` — 按 doc_id 删除
    - `save(path)` / `load(path)` — 持久化
  - 数据路径：`backend/data/` 目录

  **Recommended Agent Profile**: `deep`
  **Parallelization**: Wave 1 (with T1-T4)
  **Blocks**: T6-T9

  **Acceptance Criteria**:
  - 建库成功：340 文档全部向量化并写入 FAISS
  - 搜索返回 top_k 条结果
  - 搜索包含元数据（content, score, title）

  **QA Scenarios**:
  ```
  Scenario: 向量库完整构建
    Tool: Bash
    Steps:
      1. cd backend && python -c "from app.rag.loader import load_knowledge_docs; from app.rag.chunker import chunk_docs; from app.rag.embedding import embed; from app.rag.vector_store import VectorStore; docs=load_knowledge_docs(); chunks=chunk_docs(docs); texts=[c['content'] for c in chunks]; vecs=embed(texts); vs=VectorStore(); vs.build(vecs, chunks); print('indexed:', vs.index.ntotal)"
    Expected: indexed > 1000
    Evidence: .sisyphus/evidence/t05-vectorstore-build.txt
  ```

---

### Wave 2 — 检索与生成 (4 Tasks)

- [ ] 6. **检索器 Retriever**

  **What to do**:
  - 封装 VectorStore.search → 返回 Top-K 结果
  - 参数：`top_k=5`（可配置），`min_score=0.0`（阈值过滤）
  - 支持查询向量化 + FAISS 搜索一步完成
  - 结果去重：同一文档的不同 chunk 保留下标最小的

  **Recommended Agent Profile**: `unspecified-high`
  **Parallelization**: Wave 2 (with T7-T9)
  **Blocks**: T10
  **Blocked By**: T4, T5

  **Acceptance Criteria**:
  - 查询"校训"返回 5 条结果
  - 每条结果含 content, score, title

- [ ] 7. **LLM 生成器 Generator**

  **What to do**:
  - 复用 `rag_hhu/rag_hhu.py` 的 `DeepSeekGenerator`（OpenAI 兼容接口）
  - 参数：`temperature=0.3`, `max_tokens=1024`
  - 重试：3 次指数退避
  - 超时：30s API 超时
  - API Key 从 `.env` 读取（`DEEPSEEK_API_KEY`）

  **Recommended Agent Profile**: `quick`
  **Parallelization**: Wave 2 (with T6, T8-T9)
  **Blocks**: T10

- [ ] 8. **Prompt 模板系统**

  **What to do**:
  - 系统提示词（System Prompt）："你是一个河海大学校园知识问答助手..."
  - 上下文模板：`基于以下参考信息回答问题：\n{context}\n\n用户问题：{question}`
  - 引用格式：`[1] 来源文档标题`
  - 约束指令：知识不足时如实说明

  **Recommended Agent Profile**: `quick`
  **Parallelization**: Wave 2 (with T6-T7, T9)
  **Blocks**: T10

- [ ] 9. **RAG 流水线 Pipeline**

  **What to do**:
  - 全流程编排：`query → embed → retrieve → build_prompt → generate → format_output`
  - 返回格式：`{answer, sources: [{title, content, score}]}`
  - 错误处理：检索失败→友好提示，API 失败→重试+降级
  - 空结果：返回"未找到相关校园信息"

  **Recommended Agent Profile**: `deep`
  **Parallelization**: Wave 2 (with T6-T8)
  **Blocks**: T10-T13

  **Acceptance Criteria**:
  - `pipeline.run("校训是什么")` 返回包含"艰苦朴素"的答案
  - 返回结果含 `sources` 列表

---

### Wave 3 — 后端集成 (4 Tasks)

- [ ] 10. **RAG 编排层 rag_service.py**

  **What to do**:
  - 后端 `app/services/rag_service.py` 封装 Pipeline 调用
  - `async def answer_question(question, user_id) → {answer, sources, from_cache}`
  - 结果写入 Redis 缓存（复用现有 QACache）
  - 结果写入 MySQL qa_record 表

  **Recommended Agent Profile**: `unspecified-high`
  **Blocked By**: T9

- [ ] 11. **AI 路由 ai.py**

  **What to do**:
  - `POST /api/ai/query` — RAG 问答（body: {question} → {answer, sources}）
  - `POST /api/ai/process` — 上传文件触发处理
  - `GET /api/ai/stats` — 知识库统计
  - `POST /api/ai/reindex` — 重建全部索引
  - 注册到 main.py

  **Recommended Agent Profile**: `deep`
  **Blocked By**: T10

- [ ] 12. **文档上传改进**

  **What to do**:
  - 支持 PDF/Word/TXT 文件上传（PPT Day4 要求）
  - 文件大小限制 ≤50MB
  - 上传 → 触发 ai/process → chunk → embed → FAISS add
  - 处理状态追踪

  **Recommended Agent Profile**: `unspecified-high`
  **Blocked By**: T11

- [ ] 13. **CLI 独立脚本**

  **What to do**:
  - 在 `ai_service/cli.py` 创建独立可运行的 CLI 脚本
  - 复用 Pipeline 逻辑，脱离 FastAPI 独立运行
  - 模式：`--ask`, `--test`, `--rebuild`, 交互模式
  - 参数：`--chunk-size`, `--overlap`, `--top-k`
  - 这个文件是 PPT Day3 的独立输出要求

  **Recommended Agent Profile**: `unspecified-high`
  **Blocked By**: T9

---

### Wave 4 — 前端 (2 Tasks)

- [ ] 14. **Chat 引用来源展示**

  **What to do**:
  - Chat.tsx 中 AI 回答下方显示引用文档卡片
  - 每张卡片：文档标题 + 内容片段预览 + 相似度徽标
  - 可点击展开/折叠
  - 样式：与现有 Ant Design 风格一致

  **Recommended Agent Profile**: `visual-engineering`
  **Blocked By**: T11

- [ ] 15. **文档上传 UI + 状态展示**

  **What to do**:
  - Documents 页面增加文件上传按钮（PDF/Word/TXT）
  - 上传后显示处理进度条
  - 文档列表增加状态标签（待处理/处理中/已完成/失败）
  - 失败时可点击"重新处理"

  **Recommended Agent Profile**: `visual-engineering`
  **Blocked By**: T12

---

### Wave 5 — 测试与收尾 (4 Tasks)

- [ ] 16. **参数对比测试 benchmark.py**

  **What to do**:
  - 测试不同 `chunk_size`（256/512/1024）对检索效果的影响
  - 测试不同 `top_k`（3/5/10）对回答质量的影响
  - 使用 CLI 测试集的 10 道题作为评估基准
  - 输出表格：参数组合 → 命中率 → 平均分

  **Recommended Agent Profile**: `unspecified-high`
  **Blocked By**: T13

- [ ] 17. **全链路验证测试 (Final QA)**

  **What to do**:
  - `python cli.py --test` 全部通过（10/10）
  - `curl GET /api/ai/stats` 返回正确统计
  - `curl POST /api/ai/query {"question":"校训是什么？"}` 返回含引用来源的答案
  - 验证 main 分支代码未被修改

  **Recommended Agent Profile**: `quick`
  **Blocked By**: T14-T16

- [ ] F1. **更新 README**
  - 记录 RAG 架构、API 端点、启动方式

- [ ] F2. **代码审查 + 提交 Nanoda**
  - 清除 print debug 语句
  - 规范文件命名和 import
  - git add + commit + push

---

## Commit Strategy

- **Wave 1-2**: `feat: RAG engine with chunker, embedding, FAISS, retriever, generator`
- **Wave 3**: `feat: backend RAG integration with /api/ai/query and document upload`
- **Wave 4**: `feat: frontend source citations and document upload UI`
- **Wave 5**: `chore: CLI benchmark, README, code review`

---

## Success Criteria

### 功能验证
```bash
# CLI 测试全部通过
python ai_service/cli.py --test  # 预期: 10/10 通过

# API RAG 问答
curl -X POST http://localhost:8002/api/ai/query \
  -H "Content-Type: application/json" \
  -d '{"question":"河海大学校训是什么？"}' \
  | python -c "import sys,json; d=json.load(sys.stdin); print('PASS' if '艰苦朴素' in d.get('answer','') else 'FAIL')"
# 预期: PASS

# 知识库统计
curl http://localhost:8002/api/ai/stats  # 预期: {docs: 340, chunks: >1000}
```

### 最终检查清单
- [ ] CLI `--test` 全部通过
- [ ] 问"校训是什么？" 正确回答
- [ ] 回答附带引用来源
- [ ] 文档上传 + 自动处理
- [ ] 不影响现有 API
- [ ] 提交 Nanoda 分支

---

> **备注**：如果用户确认砍掉 Reranker/BM25/通义千问 的决策，此计划可立即执行
