# MVP 后的单 Agent 路线

只有直接 RAG 达到评测目标后才引入 LangGraph。普通事实问题继续走低延迟 RAG；多条件
比较、跨文档汇总和办事规划问题才进入 Agent。

首阶段只提供只读工具：

- `search_campus_knowledge(query, filters)`
- `get_document_metadata(document_id)`
- `compare_policies(query, date_or_department)`
- `get_current_date()`

约束：最多 4 次工具调用、统一总超时、记录完整 trace、禁止写数据库和替用户执行校园
事务。Agent 的最终回答仍经过 `[Sx]` 引用校验；任何工具结果都按不可信数据处理。

验收采用同一评测集增加多跳子集，对比直接 RAG 与 Agent 的正确率、延迟和 Token 成本。
只有多跳收益显著且成本可接受时才默认启用。多 Agent、GraphRAG、在线官网查询、自动
执行事务都不是当前优先级。
