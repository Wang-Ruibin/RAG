# Agent + RAG 下一阶段路线

当前 LLM + RAG 基线已经具备混合检索、证据充分性检查、受控联网、隐藏 QA 快速层、
人工纠错和引用校验。下一阶段引入 Agent 时，普通事实问题继续走低延迟直接 RAG；只有
多条件比较、跨文档汇总、办事规划和需要多次检索的问题才进入 Agent，不能削弱现有路径。
直接路径固定遵循“QA 关联证据核验 → 完整 RAG → 河海大学范围门控 → 联网或拒答”，
Agent 不能从证据不足的 QA 直接跳过完整知识库检索，也不能绕过最终引用连续化处理。

首阶段只提供只读工具：

- `search_campus_knowledge(query, filters)`
- `get_document_metadata(document_id)`
- `compare_policies(query, date_or_department)`
- `get_current_date()`
- `search_public_web(query)`（复用现有河海大学范围门控和免费搜索提供者）

约束：最多 4 次工具调用、统一总超时、记录完整 trace、禁止写数据库和替用户执行校园
事务。网页工具只处理河海大学相关问题，不能绕过当前校外拒答策略。Agent 的最终回答仍
经过 `[Sx]/[Wx]` 引用校验；任何工具结果都按不可信数据处理。

验收采用同一评测集增加多跳子集，对比直接 RAG 与 Agent 的正确率、延迟和 Token 成本。
只有多跳收益显著且成本可接受时才默认启用。微信/OpenClaw 等消息渠道属于接入层，必须
复用同一认证、范围门控和引用式回答服务，不在渠道代码中复制 RAG。多 Agent、GraphRAG、
自动写数据库和自动执行校园事务都不是当前优先级。
