# CampusQA 架构索引

本文件原先是一份基于 Python 3.12、Vue、Redis、Chroma 和默认 Agent 的设想，已与实际
MVP 实现不一致。当前权威架构文档为：

- [系统架构与数据流](docs/architecture.md)
- [API 与 SSE 协议](docs/api.md)
- [MVP 后 Agent 路线](docs/agent_roadmap.md)

当前实现采用 Python 3.11 + FastAPI、React 19、MySQL、FAISS/BM25、本地 BGE 和
DeepSeek。MySQL 只保存权限、任务和问答历史等业务数据；正文、chunk、metadata 和向量
进入课件指定的独立 FAISS 知识库，索引可由原子知识工件重建；Agent 不阻塞课程 MVP
验收。
