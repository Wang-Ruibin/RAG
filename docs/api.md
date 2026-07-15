# CampusQA API 与 SSE 协议

Swagger：服务启动后访问 `/docs`。除 SSE 外，所有 JSON 使用：

```json
{"code": 200, "message": "ok", "data": {}, "timestamp": "2026-07-15T00:00:00Z"}
```

`Authorization: Bearer <JWT>` 用于需要登录的接口。管理员接口额外要求 `ADMIN` 角色。

## 认证与用户

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| POST | `/api/auth/register` | 公开 | 姓名、邮箱、8–72 位密码，创建学生 |
| POST | `/api/auth/login` | 公开 | 返回 JWT 和用户 |
| GET | `/api/auth/me` | 登录 | 当前用户 |
| GET | `/api/admin/users` | 管理员 | 用户列表 |
| PATCH | `/api/admin/users/{id}` | 管理员 | 修改角色/启停，禁止自停用和自降级 |

## 文档

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| POST | `/api/documents` | 管理员 | multipart 上传，返回 202 和 job ID |
| GET | `/api/documents` | 管理员 | `page,size,q,status_filter,category` |
| GET | `/api/documents/{id}` | 管理员 | 文档状态和错误 |
| PATCH | `/api/documents/{id}` | 管理员 | 编辑标题、分类、来源 URL 和发布日期 |
| POST | `/api/documents/{id}/reindex` | 管理员 | 后台重新处理，返回 202 |
| DELETE | `/api/documents/{id}` | 管理员 | 删除原文件和 FAISS 知识库中的文本块/向量 |

文档状态：`QUEUED | PROCESSING | READY | FAILED | DELETING`。处理阶段：
`SAVED | EXTRACTING | CLEANING | CHUNKING | EMBEDDING | INDEXING | COMPLETE`。
上述接口全部在后端强制 `ADMIN`；普通用户即使手工构造 URL 也会返回 403，前端同时不显示
知识库菜单和管理路由。

## 问答与历史

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| POST | `/api/chat` | 登录 | 同步问答，便于 Swagger 和测试 |
| POST | `/api/chat/stream` | 登录 | 正式 POST SSE 问答 |
| GET | `/api/conversations` | 登录 | 当前用户会话列表 |
| GET | `/api/conversations/{id}` | 所有者 | 会话与消息 |
| DELETE | `/api/conversations/{id}` | 所有者 | 删除会话和消息 |
| GET | `/api/health` | 公开 | 数据库连通性、版本、模型和 FAISS 索引状态 |
| GET | `/api/stats` | 登录 | 文档、chunk、用户和会话数 |

请求体：

```json
{"question": "2026年9月计算机等级考试何时报名？", "conversation_id": null}
```

固定来源结构：

```json
{
  "chunk_id": 1,
  "document_id": 1,
  "title": "文档标题",
  "source_url": "https://example.edu.cn/page",
  "published_at": "2026-01-01",
  "score": 0.91,
  "snippet": "命中的原文片段"
}
```

## SSE 事件

响应类型为 `text/event-stream`，每个事件使用 `event:` 和 JSON `data:`：

```text
event: start
data: {"conversation_id":1,"message_id":2}

event: sources
data: {"items":[...],"low_confidence":false}

event: delta
data: {"text":"报名时间为"}

event: done
data: {"latency_ms":1234,"model":"deepseek-v4-flash"}
```

异常事件为 `error`，包含稳定 `code` 和友好 `message`。浏览器主动中止时消息状态写为
`CANCELLED`；上游或服务异常写为 `ERROR`。前端不能把问题放到 GET URL 中。
