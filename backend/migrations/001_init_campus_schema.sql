-- ============================================================================
-- CampusQA 校园知识问答助手 — MySQL 数据库初始化脚本
-- 目标数据库：MySQL 8.0+
-- 字符集：utf8mb4（支持表情符号和生僻字）
-- ============================================================================

CREATE DATABASE IF NOT EXISTS campus_qa
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE campus_qa;


-- ============================================================================
-- 2. 用户表
-- 多角色：学生 / 教师 / 管理员
-- ============================================================================
CREATE TABLE users (
    id              INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    username        VARCHAR(50)     NOT NULL COMMENT '登录账号（学号/工号）',
    password_hash   VARCHAR(255)    NOT NULL COMMENT '密码哈希',
    real_name       VARCHAR(50)     NOT NULL COMMENT '真实姓名',
    email           VARCHAR(100)    DEFAULT NULL COMMENT '邮箱',
    phone           VARCHAR(20)     DEFAULT NULL COMMENT '手机号',
    role            ENUM('student', 'teacher', 'admin') NOT NULL DEFAULT 'student'
                    COMMENT '角色: student=学生, teacher=教师, admin=管理员',
    avatar_url      VARCHAR(500)    DEFAULT NULL COMMENT '头像地址',
    is_active       TINYINT(1)      NOT NULL DEFAULT 1,
    last_login_at   DATETIME        DEFAULT NULL COMMENT '最后登录时间',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_username (username),
    UNIQUE KEY uk_email (email),
    INDEX idx_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='用户表（学生/教师/管理员）';


-- ============================================================================
-- 3. 校园知识库文档表 (写入向量数据库)
-- 涵盖：校园概况 / 规章制度 / 办事流程 / 校园资讯 / 通用
-- ============================================================================
CREATE TABLE campus_documents (
    id              INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    title           VARCHAR(200)    NOT NULL COMMENT '文档标题',
    content         MEDIUMTEXT      NOT NULL COMMENT '文档内容（Markdown）',
    category        ENUM('campus_info', 'policy', 'flow', 'news', 'general')
                    NOT NULL COMMENT '文档分类',
    tags            JSON            DEFAULT NULL COMMENT '标签数组 ["tag1","tag2"]',
    valid_from      DATE            DEFAULT NULL COMMENT '生效日期（制度版本管理）',
    valid_until     DATE            DEFAULT NULL COMMENT '失效日期',
    view_count      INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '访问次数',
    is_active       TINYINT(1)      NOT NULL DEFAULT 1,
    created_by      INT UNSIGNED    DEFAULT NULL COMMENT '创建者 user_id',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_category (category),
    INDEX idx_valid_date (valid_from, valid_until),
    INDEX idx_active (is_active),
    FULLTEXT INDEX ft_content (title, content) WITH PARSER ngram
                    COMMENT '中文全文索引，用于 BM25 关键词检索',
    CONSTRAINT fk_doc_creator FOREIGN KEY (created_by) REFERENCES users(id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='校园知识库文档（campus_info/policy/flow/news/general）';


-- ============================================================================
-- 10. 对话会话表  Agent
-- 持久化对话历史 保存 context JSON（当前课程/部门/意图）Agent 恢复上下文时读取
-- ============================================================================
CREATE TABLE conversations (
    id              INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED    NOT NULL COMMENT '用户 ID',
    title           VARCHAR(200)    DEFAULT NULL COMMENT '会话标题（自动生成）',
    context         JSON            DEFAULT NULL COMMENT '上下文状态（当前课程/部门等）',
    message_count   INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '消息总数',
    is_active       TINYINT(1)      NOT NULL DEFAULT 1,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_user (user_id),
    INDEX idx_updated (updated_at),
    CONSTRAINT fk_conv_user FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='对话会话表';


-- ============================================================================
-- 11. 消息表  Agent
-- 单条对话消息   拼接历史 content 作为 LLM 的 chat_history
-- ============================================================================
CREATE TABLE messages (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT UNSIGNED    NOT NULL COMMENT '所属会话',
    role            ENUM('user', 'assistant', 'system') NOT NULL COMMENT '消息角色',
    content         MEDIUMTEXT      NOT NULL COMMENT '消息内容',
    msg_metadata    JSON            DEFAULT NULL COMMENT '元数据（意图/来源/耗时等）',
    tokens_used     INT UNSIGNED    DEFAULT 0 COMMENT '消耗 token 数',
    feedback_score  TINYINT         DEFAULT NULL COMMENT '用户反馈 (-1/0/1)',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_conversation (conversation_id),
    INDEX idx_role (role),
    INDEX idx_created (created_at),
    FULLTEXT INDEX ft_msg_content (content) WITH PARSER ngram,
    CONSTRAINT fk_msg_conversation FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='对话消息表';


-- ============================================================================
-- 12. 文档访问日志表  RAG调优  (重排序+ 合并)
-- 追踪知识库文档的访问情况，用于热门统计和改进 RAG 检索
-- ============================================================================
CREATE TABLE document_access_logs (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    document_id     INT UNSIGNED    DEFAULT NULL COMMENT '被访问的文档 ID',
    user_id         INT UNSIGNED    DEFAULT NULL COMMENT '访问者 ID',
    query_text      VARCHAR(500)    DEFAULT NULL COMMENT '用户查询文本',
    intent_type     VARCHAR(50)     DEFAULT NULL COMMENT '意图类型',
    source          ENUM('agent', 'direct_retrieval', 'faq_match')
                    NOT NULL DEFAULT 'agent' COMMENT '访问来源',
    latency_ms      INT UNSIGNED    DEFAULT 0 COMMENT '检索耗时（毫秒）',
    score           DECIMAL(5,4)    DEFAULT NULL COMMENT '检索分数',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_document (document_id),
    INDEX idx_user (user_id),
    INDEX idx_intent (intent_type),
    INDEX idx_created (created_at),
    INDEX idx_date_intent (created_at, intent_type)
                    COMMENT '用于按时间段聚合统计'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='知识库文档访问日志';

