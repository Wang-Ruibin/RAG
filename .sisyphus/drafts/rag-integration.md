# Draft: RAG 集成 — 校园问答助手

## 用户需求
1. 文档 RAG 化：知识文档向量化、用户输入向量化、语义邻近查询、拼接提示词、AI 根据 RAG 检索回复
2. 参考 rag_hhu 最小脚本、PPT Day3/4 要求、架构设计文档
3. 要求全量：切分/Embedding/FAISS/检索/Prompt/LLM/流式/重排序/混合检索/参数对比/CLI
4. 分数最大化的评估导向

## 技术决策
- Embedding：BAAI/bge-small-zh-v1.5（384维，中文优化，~12MB）
- 向量库：FAISS IndexFlatIP（纯内积）
- 检索：纯 FAISS TopK（不搞 BM25 混合，340 条文档不需要）
- 重排序：❌ 砍掉（1.1GB 模型，PPT 没明确要求 Rerank）
- LLM：DeepSeek API（已有 Key），**不接**通义千问
- 切分：RecursiveCharacterTextSplitter（LangChain）
- 流式：**延后**到 stretch goal
- 架构：**合并进 backend**，不搞独立微服务（PPT 没明确要求分离）
- CLI：保留（Day3 PPT 明确要求）

## Metis 重要发现
- knowledge_docs 有 340 个 .md，不是 299（README 写错了）
- 部分 .md 有重复标题、HTML 导航残留（上一篇/下一篇）、空格标题
- 文件名含中文特殊字符（《》、空格），pathlib 需测试 Windows 兼容
- Chat.tsx 接口已有 sources 字段，RAG 集成可直接复用
- Python 3.11 兼容性需验证

## 项目结构（最终）
- backend/app/rag/ — RAG 引擎（内嵌，非独立服务）
- backend/app/services/rag_service.py — 编排层
- backend/app/routers/ai.py — API 路由
- ai_service/cli.py — 独立 CLI 脚本（PPT 要求）
- ai_service/benchmark.py — 参数对比
- frontend/ — 引用来源展示

## 用户确认项
- [ ] 合并进 backend（不单独开微服务）
- [ ] 砍掉 Reranker
- [ ] 砍掉 通义千问 fallback
- [ ] 延后 SSE 流式
- [ ] 保留 CLI + Benchmark
