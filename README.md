# CampusQA - 河海大学校园知识问答助手

基于 LLM + RAG / Agent + RAG 构建的河海大学校园知识问答系统。

## 快速开始

### 环境要求

- Python 3.12+
- MySQL 8.0+
- Redis 7.0+

### 安装

```bash
# 克隆仓库
git clone https://github.com/Wang-Ruibin/RAG.git
cd RAG

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

### 配置

复制并编辑环境变量文件：

```bash
cp .env.example .env
# 编辑 .env 填入 API Key、数据库连接等配置
```

## knowledge_docs 目录说明

知识文档库，存放用于 RAG 检索的河海大学相关知识文档。

| 文件夹 | 内容 | 文档数 |
|--------|------|--------|
| `news/` | 学校新闻、学术动态、科研成果、通知公告 | 198 |
| `academic/` | 教务处通知、研究生院、课程安排、教学工作 | 141 |
| `academic_files/` | 从 PDF/XLSX/PPTX 提取的课程清单、校历、使用指南等 | 16 |
| `university_info/` | 学校概况、院系设置、职能部门、校园文化 | 17 |
| `departments/` | 各学院简介、师资队伍、科研介绍 | 213 |
| `admin/` | 职能部门（资产处、基建处、审计处等） | 111 |
| `alumni/` | 校友会、教育发展基金会、捐赠项目 | 133 |
| `third_party/` | 百度百科、维基百科、教育部、人民网等第三方来源 | 11 |
| `research/` | 科技处、社科处等科研平台信息 | 121 |
| `campus_life/` | 学生工作部等校园生活信息 | 65 |

**来源**：河海大学主站 (hhu.edu.cn) 及各子域名、16个学院官网、12个职能部门网站、百度百科、维基百科、教育部等。每篇文档均标注了网页来源 URL。

## 参考文件

`campus_assistant_arch.md` — 来自其他项目的校园问答助手架构设计文档，作为本项目的参考。其中的技术栈选型（FastAPI + LangChain + ChromaDB）、分层架构设计、多源路由策略等思路可供借鉴。
