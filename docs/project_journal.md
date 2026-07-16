# CampusQA 项目实施与答辩素材日志

> 本文是项目事实记录和周六 Beamer 答辩 PPT 的主要内容源。实现过程中持续更新，
> 只记录可公开信息，绝不记录 API Key、密码或本地密钥。

## 一、项目背景与目标

- 场景：河海大学官网、学院、教务和校园生活信息分散，学生难以快速找到可信答案。
- 目标：构建一个基于 LLM + RAG 的中文校园知识问答助手，支持知识库管理、
  引用式问答、流式输出、多轮会话、历史记录和角色权限。
- 三天 MVP：覆盖实训课件六天要求，形成可在 WSL 本机稳定演示的完整 Web 应用。
- 长期方向：先用评测证明 RAG 可靠，再加入有工具边界的单 Agent。

## 二、输入资料与调研

- 课程资料：Day 1 至 Day 6，覆盖环境/架构、认证、RAG、知识库、AI 问答、测试发布。
- 初始知识库：`knowledge_docs/` 共 1,026 篇河海大学相关 Markdown，约 5.5 MB；联调阶段
  新增 1 篇计算示例，当前版本化语料共 1,027 篇。
- 指定 Demo：`llmlearning-x/campus-practice`，学习 FastAPI、SQLite、FAISS、SSE、
  引用和会话；针对同步入库、全局锁、删除重建和缺少评测等问题重新设计。
- 其他参考：Kotaemon（混合检索/引用体验）、RAGFlow（解析/可追溯）、
  FlagEmbedding（BGE）、LangGraph（后续 Agent）、Ragas（评测方法）。

## 三、关键技术决策

1. 使用 React + FastAPI 单后端，不采用课件中的 Spring Boot + Python 双服务，
   原因是三天周期、当前环境无 Java/Docker，单后端更容易完成和讲清完整链路。
2. 根据用户对数据边界的澄清，MySQL 只存用户/RBAC、文档任务元数据、会话和消息；
   校园正文、chunk、metadata 和 embedding 全部进入独立知识库。课件 Day 3/Day 4 明确
   指定 FAISS `IndexFlatIP`，实现用 `IndexIDMap2(IndexFlatIP)` 增加稳定向量 ID。
3. 每篇资料以原子 NPZ 工件保存文本块、来源 metadata 和向量；FAISS/BM25 可从这些工件
   重建。自动化测试仍用临时 SQLite，但 SQL schema 中同样不存在 chunk/embedding 表。
4. 本地 `bge-small-zh-v1.5` 负责向量化，`bge-reranker-base` 负责精排，
   不依赖额外 Embedding 付费账号；默认适配 8 GB CPU 环境，也可在 Windows/Linux/WSL
   使用 CUDA 12.8/13.0 构建自动加速两个 BGE 模型。
5. LLM 使用 DeepSeek OpenAI-compatible API，Key 只从 `DEEPSEEK_API_KEY` 读取；
   模型默认 `deepseek-v4-flash`，避免使用即将下线的旧别名。
6. 检索采用向量 Top20 + BM25 Top20 + RRF Top12 + Rerank Top5，再按最低分和相对分差
   过滤弱相关项，兼顾语义问题与教室编号、部门名、政策名称等精确关键词。
7. 上传立即返回 202，单工作线程后台解析/切块/向量化；索引锁不覆盖 LLM 流式生成。
8. 每项事实要求 `[Sx]` 引用，资料不足明确拒答；来源卡展示标题、日期、URL 和片段，
   不把内部排序分误标成相似度概率。

## 四、GitHub 发布与安全约束

- `.env`、本地 AI 覆盖配置、数据库、上传文件、FAISS 索引、模型权重和缓存不提交。
- 仓库只提交 `.env.example`，其中只包含变量名和安全默认值。
- 默认管理员通过 CLI 创建；自动化演示凭据只保存在被忽略的本机 `.env`。
- 最终发布前执行 Git 跟踪文件检查、敏感模式扫描、无用文件清理和文档一致性检查。

## 五、实施记录

### 2026-07-15：规划与工程初始化

- 完成六天课件文本抽取和指定 Demo 核心代码审查。
- 确认本机环境：Node 22、Python 3.11、uv；无 Java、Docker、GPU；约 8 GB 内存。
- 创建 `AGENTS.md`，固化架构不变量、命令、测试和 Definition of Done。
- 建立 `pyproject.toml`、`.env.example`、Alembic 和后端分层骨架。
- 建立用户、文档任务元数据、会话和消息业务模型；后续按用户要求将 chunk/embedding
  从 ORM 完全移除。
- 开始实现结构感知解析、递归切块和本地 BGE Embedding 接口。
- 根据实际环境将业务数据库调整为 MySQL；数据库口令只由本机 `.env` 注入，测试继续使用临时 SQLite。

### 2026-07-15：MVP 业务链路完成

- 后端完成认证、RBAC、用户管理、文档 CRUD、后台处理状态机、同步问答、POST SSE、
  会话归属校验和历史消息状态持久化。
- RAG 完成 Markdown/TXT/PDF/DOCX 解析、标题路径切块、BGE、FAISS IDMap2、中文 BM25、
  RRF、Cross-Encoder、本地资料约束 Prompt 和生成后引用编号过滤。
- 前端完成登录注册、路由鉴权、聊天/停止生成/历史会话、来源卡、知识库管理、用户管理、
  安全 Markdown 和移动端基础样式。
- 知识库管理页仅管理员可见，并由后端 RBAC 二次兜底；实现上传、列表/详情、元数据编辑、
  重新处理、删除和状态轮询，普通用户调用知识库接口返回 403。
- 后端现有 18 个测试，覆盖配置安全、解析切块、RRF、引用、认证权限、知识库管理员边界、
  会话越权、独立知识工件入库/编辑/删除、HTTP 生命周期、低置信拒答和 SSE 完成态；
  SSE 上游异常详情不会返回浏览器。
- 前端 ESLint、Vitest 和生产构建通过；npm 审计 0 漏洞。四个页面改为路由懒加载后，
  消除了大于 500 KB 的单 chunk 警告，聊天页约 45 KB gzip、运行时核心约 151 KB gzip。

### 2026-07-15：全量语料与真实评测

- CPU-only PyTorch 2.13.0 安装并验证，`cuda=False`；两个 BGE 模型已缓存并完成前向。
- Windows MySQL 9.7.1 已由 WSL 通过 `127.0.0.1:3306` 实际连接；Alembic 创建 6 张
  业务表，复核不存在 `chunks/embeddings/vectors` 表。
- 全量导入 1,026 篇，最终 READY 1,026、FAILED 0、chunk 3,867；独立知识工件 1,026、
  FAISS `ntotal` 3,867、manifest 3,867，与 MySQL 管理统计三者一致。
- 建立 50 条评测集：30 单轮、10 多轮、10 无答案。
- Dense-only：Hit@5 0.900、MRR@5 0.844、P95 59.56 ms。
- Hybrid：Hit@5 0.950、MRR@5 0.861、P95 43.86 ms。
- 完整精排 12×512：MRR 0.919，但 P95 7.78 秒。
- 调优精排 5×256：独立 FAISS 知识库复跑 Hit@5 0.950、MRR 0.919、P95 1.462 秒、
  OOD 误接受率 0%；采用。
- 拒答阈值按评测固化：精排 0.7256；无精排 Hybrid 0.6526。
- 真实 DeepSeek 冒烟通过：管理员登录、知识库列表、同步 `/api/chat` 和 POST SSE 均成功；
  命中 2026 年计算机等级考试通知，返回官网 URL、带 `[S1]` 的答案和
  `start/sources/delta/done` 事件。
- 运行 5 题真实生成样本：所有题均生成可解析引用；严格 gold 标题引用精度 0.667。
  该代理指标会把复核通知、补选通知、学院复试细则等合理补充来源算错，因此重命名为
  `citation_gold_title_precision`，不冒充尚未完成人工核验的事实—来源正确率。
- 真实 `.env`、MySQL 数据、知识工件、FAISS 索引、模型缓存和前端构建产物均由
  `.gitignore` 排除；公开文档只记录变量名，不记录真实 Key 或密码。
- 新增 `scripts/check_secrets.py`：只扫描 Git 会纳入的文件，将内容与本机 `.env` 密钥值
  及通用 Key 模式比较；命中时只输出文件名和规则，不回显秘密本身。

### 实施中遇到的问题与解决

1. 用户曾在对话中暴露旧 LLM Key：必须在供应商后台撤销；新的配置只存在本机 `.env`。
   代码与日志均不打印 Key，真实同步/SSE 冒烟已验证可用。
2. 默认 PyTorch 解析会在 Linux 下载数 GB CUDA 包：采用 uv 冲突 extra 和官方独立
   index，部署者必须在 `cpu/cu128/cu130` 中选择一个；CPU wheel 无 NVIDIA 依赖，GPU
   机器又能复用同一份锁文件。运行命令加 `--no-sync`，防止把已选择的构建重新解析。
3. npm 中误设了不存在的 React 插件 7.x：查询注册表后对齐 Vite 8 / plugin-react 6，
   安装 400 个包，审计 0 漏洞。
4. Codex 文件系统沙箱会阻断 AnyIO 跨线程唤醒：空 FastAPI 也可复现；测试改用 ASGI
   AsyncClient，并在受控非沙箱环境验证，避免为沙箱问题改坏生产代码。
5. 模型已缓存仍会做 Hugging Face HEAD 请求：增加 `MODEL_LOCAL_FILES_ONLY` 配置，
   断网入库验证成功。
6. 完整 Reranker CPU 延迟过高：用固定评测集比较候选数和长度，选出质量不降、延迟下降
   的 5×256 配置；最终热检索复跑 P95 1.462 秒，刚好达到 1.5 秒目标。
7. 初始管理员使用 `.local` 邮箱被 `email-validator` 拒绝：改为合法的
   `admin@campusqa.cn`，同步更新本机配置和 MySQL，真实登录通过。
8. 用户要求“资料进入知识库而非数据库”：停止在途导入，回看课件确认指定 FAISS，
   移除 SQL `Chunk` 模型并重构为原子知识工件 + FAISS/BM25；中断残留清理后全量导入。

### 2026-07-15：项目收尾与发布检查

- 清理旧 SQLite 数据库、旧索引和 1,026 个未被 MySQL 引用的上传副本；保留当前
  1,026 个原文件、1,026 个知识工件和 3,867 个向量，最终一致性为 true。
- 清理真实冒烟产生的 2 条重复管理员会话及级联消息，首次演示历史保持空白。
- `.gitignore` 明确排除 `.env`、AI 工具配置、`.venv`、模型、上传、FAISS 知识库、
  Node 依赖和前端构建产物；最终发布扫描 1,115 个可纳入 Git 的文件，0 密钥命中。
- `uv.lock` 在官方索引上升级并锁定 129 个包；分别导出 CPU、CUDA 12.8、CUDA 13.0
  三份运行时 requirements。Embedding 与 Reranker 增加 `MODEL_DEVICE=auto/cpu/cuda`，
  有可用 CUDA 时自动使用显卡，FAISS 继续用 CPU 版本保证 Windows 可安装性。
- README 扩充为跨平台协作部署手册，写明 Windows 原生/WSL MySQL、环境变量、硬件选择、
  初始化、测试、故障排查、项目树以及全部代码和配置文件职责；新增跨平台
  `scripts/start.py`，Bash 包装器复用同一入口。
- 最终验证：Ruff 通过，后端 19/19、覆盖率 75%，前端 ESLint/Vitest/生产构建通过；
  `uv lock --check`、`git diff --check` 和密钥扫描通过。
- 推送前第二次清理删除所有 `__pycache__`、pytest/ruff 缓存、TypeScript build info，
  并复查 `.tmp/.bak/.orig/.log/.DS_Store/Thumbs.db` 等临时模式均无残留；本机 `.venv`、
  `data`、`node_modules` 和 `frontend/dist` 保留但确认全部被 Git 忽略。

### 2026-07-16：运行联调与问答体验修复

- FAISS 启动时优先加载已保存索引并校验 manifest/NPZ 工件；损坏或不一致时自动重建。
- 启动阶段预热 Embedding 与 Reranker，并为 CPU 推理增加串行保护；热检索通常约 1 秒。
- 修复上传文档热处理的标题回退，新增 `计算题.txt` 后无需重启即可进入知识库；当前本机
  状态为 1,027 篇文档、3,868 个 chunk。
- 多轮检索改为本地上下文依赖判断，普通新问题不再额外调用一次 LLM 改写。
- 增加边界词法命中放行和强相关上下文过滤：最高来源通过拒答判断后，后续来源需达到
  最低精排分且与最高分差不超过阈值，最多 5 条；排序分不再展示成相似度百分比。
- SSE 只发送最终来源，修复回答引用 `[S1]` 但页面仍展示 5 条弱相关候选的问题。
- 修复知识库真实后端分页、每页数量切换，以及删除会话事件冒泡导致的重复请求。
- 验证结果：Ruff 通过，后端 26/26；前端 ESLint、Vitest、生产构建通过。真实提问
  “1+1等于几”端到端 9.885 秒，最终仅保留强相关的“计算题”来源。

## 六、Beamer 答辩建议结构

1. 标题页：河海大学校园知识问答助手、LLM + RAG、姓名和日期。
2. 背景痛点：信息分散、官网搜索成本、纯 LLM 幻觉和时效问题。
3. 需求与边界：学生/管理员四大模块，三天 MVP，Agent 不阻塞验收。
4. 总体架构：React、FastAPI、MySQL 业务库、FAISS 向量知识库、BGE、DeepSeek。
5. 文档入库：202 状态机、解析清洗、500/80 切块、稳定 ID、原子索引。
6. 混合检索：Dense/BM25/RRF/Rerank 的角色与参数。
7. 可信生成：不可信资料、只依赖上下文、引用校验、低置信拒答、时效提示。
8. 业务与安全：JWT/RBAC、会话归属、Argon2、上传边界、密钥治理。
9. 前端体验：流式、停止、来源卡、历史、管理员处理进度。
10. 评测结果：1,026/3,867、三种检索对比、阈值和真实延迟权衡。
11. 演示：知识题、多轮、无答案、上传处理、Swagger。
12. 总结与路线：ONNX/INT8、MySQL 实联调、引用事实评测、只读 LangGraph Agent。

## 七、待补充的答辩证据

- MySQL/FAISS/DeepSeek 实联调已有命令证据，仍需补页面截图用于 PPT。
- 多题首 token 延迟、全量引用正确率和人工事实忠实率。
- 页面截图：登录、聊天引用、知识库处理状态、用户管理。
- 典型问题、无答案问题、多轮追问和异常恢复演示。
- Beamer 最终视觉主题、架构图导出和参数对比图。
