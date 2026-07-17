# CampusQA API 与 SSE 协议

Swagger：服务启动后访问 `/docs`。除 SSE 外，所有 JSON 使用：

```json
{"code": 200, "message": "ok", "data": {}, "timestamp": "2026-07-15T00:00:00Z"}
```

`Authorization: Bearer <JWT>` 用于需要登录的接口。管理员接口额外要求 `ADMIN` 角色。

## 认证与用户

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| POST | `/api/auth/register` | 公开 | 姓名、邮箱、8–72 位密码，创建普通用户（后端值 `STUDENT`） |
| POST | `/api/auth/login` | 公开 | 返回 JWT 和用户 |
| GET | `/api/auth/me` | 登录 | 当前用户 |
| GET | `/api/admin/users` | 管理员 | 用户列表 |
| PATCH | `/api/admin/users/{id}` | 管理员 | 修改角色/启停，禁止自停用和自降级 |

## 文档

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| POST | `/api/documents` | 管理员 | multipart 上传，返回 202 和 job ID |
| GET | `/api/documents` | 登录 | `page,size,q,status_filter,category` |
| GET | `/api/documents/{id}` | 登录 | 文档状态和错误 |
| GET | `/api/documents/{id}/preview` | 登录 | `offset,limit`，最大 50,000 字符；PDF/DOCX 返回提取文本 |
| GET | `/api/documents/{id}/download` | 登录 | 使用安全原文件名下载 |
| PATCH | `/api/documents/{id}` | 管理员 | 编辑标题、分类、来源 URL 和发布日期 |
| POST | `/api/documents/{id}/reindex` | 管理员 | 后台重新处理，返回 202 |
| DELETE | `/api/documents/{id}` | 管理员 | 删除原文件和 FAISS 知识库中的文本块/向量 |

文档状态：`QUEUED | PROCESSING | READY | FAILED | DELETING`。处理阶段：
`SAVED | EXTRACTING | CLEANING | CHUNKING | EMBEDDING | INDEXING | COMPLETE`。
列表、详情、预览和下载使用 `CurrentUser`；上传、编辑、重建和删除强制 `ADMIN`。
公开前端路由为 `/knowledge`，旧 `/admin/documents` 重定向到新路由。

## 问答与历史

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| POST | `/api/chat` | 登录 | 同步问答，便于 Swagger 和测试 |
| POST | `/api/chat/stream` | 登录 | 正式 POST SSE 问答 |
| POST | `/api/messages/{id}/knowledge-task` | 消息所有者 | 将已完成回答加入知识库，返回 202 |
| GET | `/api/messages/{id}/knowledge-task` | 消息所有者 | 查询该回答的入库任务 |
| GET | `/api/knowledge-tasks/{id}` | 任务所有者 | 轮询入库任务状态 |
| POST | `/api/messages/{id}/correction` | 消息所有者 | 提交正确答案；已拒绝/失败记录可修改重提 |
| GET | `/api/admin/answer-corrections` | 管理员 | 按 `status_filter`、`page`、`size` 查询纠错 |
| POST | `/api/admin/answer-corrections/{id}/approve` | 管理员 | 审核问题/答案及可选 READY 文档 ID，返回 202 |
| POST | `/api/admin/answer-corrections/{id}/reject` | 管理员 | 记录并向用户展示拒绝原因 |
| GET | `/api/conversations` | 登录 | 当前用户会话列表 |
| GET | `/api/conversations/{id}` | 所有者 | 会话与消息 |
| DELETE | `/api/conversations/{id}` | 所有者 | 删除会话和消息 |
| GET | `/api/health` | 公开 | 数据库连通性、版本、模型和 FAISS 索引状态 |
| GET | `/api/stats` | 登录 | 文档、chunk、用户和会话数 |

请求体：

```json
{"question": "2026年9月计算机等级考试何时报名？", "conversation_id": null}
```

本地知识库来源结构：

```json
{
  "source_type": "KNOWLEDGE_BASE",
  "chunk_id": 1,
  "document_id": 1,
  "title": "文档标题",
  "source_url": "https://example.edu.cn/page",
  "published_at": "2026-01-01",
  "score": 0.91,
  "snippet": "命中的原文片段",
  "citation_index": 1
}
```

网页搜索来源不包含 chunk/document ID，使用独立的网页地址与站点信息：

```json
{
  "source_type": "WEB_SEARCH",
  "citation_index": 1,
  "title": "河海大学通知",
  "url": "https://www.hhu.edu.cn/news",
  "site_name": "河海大学",
  "domain": "www.hhu.edu.cn",
  "published_at": "2026-07-02",
  "snippet": "官网通知摘要"
}
```

`score` 是 Cross-Encoder 的内部排序分，不是经过校准的相似度概率，前端不显示百分比。
后端只保留通过绝对分数和相对分差过滤的强相关来源，最多 5 条；`citation_index` 与回答
中的 `[Sx]` 编号保持一致。当次实时网页来源使用 `[Wx]`；网页归档进入本地知识库后使用
`[Sx]`，但 `source_type` 仍保留 `WEB_ARCHIVE` 以标明来源性质。审核通过的用户纠错使用
`USER_CORRECTION` 和 `[Sx]`，并只返回 `contributor_name`，不向问答页公开邮箱。

纠错状态为 `PENDING | PROCESSING | APPROVED | REJECTED | FAILED`。批准后后台生成普通
`USER_CORRECTION` Markdown 文档并走切块、Embedding、FAISS/BM25 完整链路；不创建隐藏
`QaEntry`。

同步问答和历史消息通过 `answer_origin` 标识
`KNOWLEDGE_BASE | WEB_SEARCH | HYBRID | NO_ANSWER`。满意回答入库任务状态为
`QUEUED | PROCESSING | COMPLETE | FAILED`；相同助手消息重复提交会返回同一任务，不会
重复生成知识条目。任务完成后返回 `qa_entry_id`；QA 是隐藏检索层，不会作为来源卡片。
知识库来源只关联原 `document_id`，网页来源分别归档并按 URL/内容去重。强 QA 命中会跳过
全库检索和再次联网，加载其关联原文后由当前模型重新生成；引用只指向本地原知识文档或
网页归档 `[Sx]`，不会直接回放历史 QA 答案。

## SSE 事件

响应类型为 `text/event-stream`，每个事件使用 `event:` 和 JSON `data:`：

```text
event: start
data: {"conversation_id":1,"message_id":2}

event: status
data: {"phase":"retrieval","message":"正在检索校园知识库…"}

event: delta
data: {"text":"报名时间为"}

event: sources
data: {"items":[...],"low_confidence":false,"answer_origin":"KNOWLEDGE_BASE","final":true}

event: done
data: {"latency_ms":1234,"model":"deepseek-v4-flash","answer_origin":"KNOWLEDGE_BASE"}
```

正常回答只发送一次最终 `sources` 事件，位于文本增量之后、`done` 之前，避免把生成前的
Top-K 弱相关候选误展示为引用来源。本地证据不足后先做河海大学范围判断：相关问题才会
发送 `web_search` 状态并调用免费多引擎或可选百度搜索；无关问题不发送该状态、不访问
网页，直接返回多样化礼貌说明。搜索未启用、失败或无结果时拒答且 `items` 为空。

打开空白问答页时的欢迎语是前端展示状态，不创建会话或消息；只有用户首次真正提问时才
创建会话。用户发送“你好”“谢谢”“再见”等简短社交消息时，服务端本地响应，
`answer_origin=NO_ANSWER`，不调用网页搜索或 LLM。

异常事件为 `error`，包含稳定 `code` 和友好 `message`。浏览器主动中止时消息状态写为
`CANCELLED`；上游或服务异常写为 `ERROR`。前端不能把问题放到 GET URL 中。
