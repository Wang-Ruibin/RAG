# 测试与评测说明

## 自动化分层

- 单元：配置 URL 安全组装、解析/清洗、标题路径切块、RRF、引用编号过滤、免费/百度
  搜索规范化与错误分类。
- 接口：注册登录、管理员权限、自停用保护、会话越权、文档只读/写权限、预览下载、
  运行时删除、QA 去重/归档、纠错审批和校外问题免联网。
- 前端：SSE 分帧解析、引用折叠与颜色、主动欢迎语、复制/点赞/倒赞、普通用户只读知识库、
  TypeScript、ESLint、Vitest、Vite 生产构建。
- 真实 RAG：50 条版本化样本，30 条知识问答、10 条多轮、10 条知识库外问题。

后端测试在 `/tmp` 创建 SQLite，使用 Fake 检索结果和 Fake LLM，不连接 MySQL、不下载
模型、不消耗 DeepSeek Token。运行：

```bash
.venv/bin/ruff check backend evals scripts
.venv/bin/pytest --cov=app --cov-report=term-missing
cd frontend && npm run lint && npm run test -- --run && npm run build
```

2026-07-17 最新自动化基线：后端 Ruff 通过、54 个 pytest 全部通过；前端 ESLint、9 个
Vitest 和生产构建通过。测试覆盖热上传与运行时删除、边界词法命中、上下文弱相关过滤、
最终来源 SSE、知识库分页/预览/下载、QA 快速命中及去重、网页归档、纠错审批、引用颜色、
主动欢迎语，以及同步/流式校外问题都不触发网页搜索等回归场景。

同日生产式启动回归和用户手工验收通过；服务可由 WSL 中的 `python scripts/start.py`
启动，并在终端出现 `Application startup complete` 后通过 `http://127.0.0.1:8000` 访问。

## 真实评测

先完成全量导入，再运行：

```bash
.venv/bin/python evals/run_eval.py --mode dense --output docs/evaluation_dense.json
.venv/bin/python evals/run_eval.py --mode hybrid --output docs/evaluation_hybrid.json
.venv/bin/python evals/run_eval.py --mode hybrid-rerank --output docs/evaluation_report.json
```

脚本输出每题 Top5 标题、排名、分数和耗时，并汇总 Hit@5、MRR@5、P95。它会遍历候选
阈值，在知识库外问题误答率不超过 10% 的约束下选择 F1 最高的拒答阈值。确认 API 成本
后可增加 `--with-generation`，评估合法引用是否指向 gold 文档。该字段命名为
`citation_gold_title_precision`，只是严格代理指标；相关补充来源可能支持答案却不匹配
单一 gold 标题，不能直接当作人工事实—来源正确率。

2026-07-15 的 CPU 实测采用 1,026 篇、3,867 个 chunk。该历史基线不包含随后加入的
`计算题.txt`、8 篇网页归档和 3 条隐藏 QA，因此原始评测 JSON 不随当前 1,035/3,883
本机运行状态改写。最终精排参数为 5 个候选、最大长度 256；独立 FAISS 知识库重构后
复跑结果为 Hit@5 0.950、MRR@5 0.919、P95 1.462 秒、知识库外误接受率 0%。完整结果与
参数对比见 `evaluation_summary.md`。

目标：

| 指标 | 目标 |
|---|---:|
| Hit@5 | ≥ 0.85 |
| MRR@5 | ≥ 0.75 |
| 引用来源正确率 | ≥ 0.90 |
| 有答案问题事实忠实率（人工复核） | ≥ 0.90 |
| 无答案问题正确拒答率 | ≥ 0.90 |
| 热检索 P95 | ≤ 1.5 s |
| 正常网络首 token P95 | ≤ 6 s |

## 手工安全冒烟

1. 普通用户访问 `/api/admin/users` 应返回 403。
2. 用户 A 读取用户 B 会话应返回 404。
3. 上传 `.exe`、超过 50 MB 文件和带路径的文件名均应被拒绝或净化。
4. 失效 JWT 返回 401；停用用户的旧 JWT 也不可用。
5. 知识文档中嵌入脚本或“忽略系统提示”的文本不应执行或改变回答规则。
6. 中止流后刷新历史，assistant 消息应为 `CANCELLED` 而非无故消失。
7. 删除/破坏 `data/knowledge_base/index` 后重启，索引应能从每篇 NPZ 知识工件重建，
   MySQL 中不应出现 `chunks/embeddings/vectors` 表。
8. 对“Python 快速排序”“红烧肉菜谱”一类校外问题，SSE 中不应出现 `web_search` 阶段；
   对省略主语的“新学期校历什么时候发布”仍应允许校内联网补充。
9. 普通用户只能预览/下载知识文档；上传、编辑、重建、删除和纠错审批均应返回 403。

真实指标、机器配置和失败样本统一记录在 `docs/evaluation_report.json` 与
`docs/project_journal.md`，不得用目标值冒充实测值。
