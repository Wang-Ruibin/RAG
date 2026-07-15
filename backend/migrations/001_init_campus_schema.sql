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
-- 1. 院系/部门表
-- 校园组织架构，树形结构（支持院-系两级）
-- ============================================================================
CREATE TABLE departments (
    id              INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100)    NOT NULL COMMENT '部门名称',
    code            VARCHAR(50)     DEFAULT NULL COMMENT '部门代码（如 CS, MATH）',
    parent_id       INT UNSIGNED    DEFAULT NULL COMMENT '上级部门 ID',
    level           TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '层级: 1=学院, 2=系/所, 3=科室',
    description     VARCHAR(500)    DEFAULT NULL COMMENT '部门简介',
    phone           VARCHAR(30)     DEFAULT NULL COMMENT '联系电话',
    location        VARCHAR(200)    DEFAULT NULL COMMENT '办公地点',
    sort_order      INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '排序',
    is_active       TINYINT(1)      NOT NULL DEFAULT 1,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_dept_code (code),
    INDEX idx_parent (parent_id),
    CONSTRAINT fk_dept_parent FOREIGN KEY (parent_id) REFERENCES departments(id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='院系/部门组织架构';


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
    department_id   INT UNSIGNED    DEFAULT NULL COMMENT '所属院系',
    avatar_url      VARCHAR(500)    DEFAULT NULL COMMENT '头像地址',
    is_active       TINYINT(1)      NOT NULL DEFAULT 1,
    last_login_at   DATETIME        DEFAULT NULL COMMENT '最后登录时间',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_username (username),
    UNIQUE KEY uk_email (email),
    INDEX idx_role (role),
    INDEX idx_department (department_id),
    CONSTRAINT fk_user_dept FOREIGN KEY (department_id) REFERENCES departments(id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='用户表（学生/教师/管理员）';


-- ============================================================================
-- 3. 校园知识库文档表
-- 涵盖：校园概况 / 规章制度 / 办事流程 / 校园资讯 / 通用
-- ============================================================================
CREATE TABLE campus_documents (
    id              INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    title           VARCHAR(200)    NOT NULL COMMENT '文档标题',
    content         MEDIUMTEXT      NOT NULL COMMENT '文档内容（Markdown）',
    category        ENUM('campus_info', 'policy', 'flow', 'news', 'general')
                    NOT NULL COMMENT '文档分类',
    department_id   INT UNSIGNED    DEFAULT NULL COMMENT '所属部门（外键）',
    tags            JSON            DEFAULT NULL COMMENT '标签数组 ["tag1","tag2"]',
    valid_from      DATE            DEFAULT NULL COMMENT '生效日期（制度版本管理）',
    valid_until     DATE            DEFAULT NULL COMMENT '失效日期',
    view_count      INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '访问次数',
    is_active       TINYINT(1)      NOT NULL DEFAULT 1,
    created_by      INT UNSIGNED    DEFAULT NULL COMMENT '创建者 user_id',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_category (category),
    INDEX idx_department (department_id),
    INDEX idx_valid_date (valid_from, valid_until),
    INDEX idx_active (is_active),
    FULLTEXT INDEX ft_content (title, content) WITH PARSER ngram
                    COMMENT '中文全文索引，用于 BM25 关键词检索',
    CONSTRAINT fk_doc_dept FOREIGN KEY (department_id) REFERENCES departments(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_doc_creator FOREIGN KEY (created_by) REFERENCES users(id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='校园知识库文档（campus_info/policy/flow/news/general）';


-- ============================================================================
-- 4. 课程表
-- ============================================================================
CREATE TABLE courses (
    id              INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    code            VARCHAR(50)     NOT NULL COMMENT '课程代码（如 CS101）',
    name            VARCHAR(200)    NOT NULL COMMENT '课程名称',
    instructor      VARCHAR(100)    NOT NULL COMMENT '授课教师',
    instructor_id   INT UNSIGNED    DEFAULT NULL COMMENT '授课教师 user_id',
    department_id   INT UNSIGNED    DEFAULT NULL COMMENT '开课院系',
    semester        VARCHAR(20)     NOT NULL COMMENT '学期（如 2026春, 2025-2026-2）',
    description     TEXT            DEFAULT NULL COMMENT '课程简介',
    credits         DECIMAL(3,1)    DEFAULT NULL COMMENT '学分',
    syllabus_path   VARCHAR(500)    DEFAULT NULL COMMENT '教学大纲文件路径',
    max_students    INT UNSIGNED    DEFAULT NULL COMMENT '容量上限',
    enrolled_count  INT UNSIGNED    DEFAULT 0 COMMENT '已选人数',
    status          ENUM('upcoming', 'active', 'ended', 'cancelled')
                    NOT NULL DEFAULT 'active' COMMENT '课程状态',
    is_active       TINYINT(1)      NOT NULL DEFAULT 1,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_course_code_semester (code, semester),
    INDEX idx_department (department_id),
    INDEX idx_instructor (instructor_id),
    INDEX idx_semester (semester),
    INDEX idx_status (status),
    FULLTEXT INDEX ft_course_name_desc (name, description) WITH PARSER ngram,
    CONSTRAINT fk_course_dept FOREIGN KEY (department_id) REFERENCES departments(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_course_instructor FOREIGN KEY (instructor_id) REFERENCES users(id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='课程信息表';


-- ============================================================================
-- 5. 课程资料文件表
-- 映射到 Chroma 向量集合的课程资料
-- ============================================================================
CREATE TABLE course_materials (
    id              INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    course_id       INT UNSIGNED    NOT NULL COMMENT '所属课程',
    title           VARCHAR(200)    NOT NULL COMMENT '资料标题',
    file_type       ENUM('pdf', 'pptx', 'docx', 'md', 'txt', 'image')
                    NOT NULL DEFAULT 'pdf' COMMENT '文件类型',
    file_path       VARCHAR(500)    NOT NULL COMMENT '文件存储路径',
    file_size       BIGINT UNSIGNED DEFAULT 0 COMMENT '文件大小（字节）',
    chunk_status    ENUM('pending', 'processing', 'ready', 'failed')
                    NOT NULL DEFAULT 'pending' COMMENT '切片状态',
    chunk_count     INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '切片数量',
    md5             VARCHAR(32)     NOT NULL COMMENT '文件 MD5 哈希（去重）',
    uploaded_by     INT UNSIGNED    NOT NULL COMMENT '上传者',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_course (course_id),
    INDEX idx_chunk_status (chunk_status),
    UNIQUE KEY uk_md5 (md5),
    CONSTRAINT fk_material_course FOREIGN KEY (course_id) REFERENCES courses(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_material_uploader FOREIGN KEY (uploaded_by) REFERENCES users(id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='课程资料文件表（映射到 Chroma 向量集合）';


-- ============================================================================
-- 6. 高频问答对（FAQ）
-- 精确匹配 + 语义匹配双通道
-- ============================================================================
CREATE TABLE faq (
    id                  INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    question            VARCHAR(300)    NOT NULL COMMENT '标准问题',
    answer              TEXT            NOT NULL COMMENT '标准答案',
    category            VARCHAR(50)     DEFAULT NULL COMMENT '分类（教务/生活/就业/其他）',
    tags                JSON            DEFAULT NULL COMMENT '标签数组',
    keywords            JSON            DEFAULT NULL COMMENT '关键词数组（用于精确匹配）',
    similar_questions   JSON            DEFAULT NULL COMMENT '相似问法数组',
    related_faq_ids     JSON            DEFAULT NULL COMMENT '关联 FAQ ID 列表',
    hit_count           INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '命中次数',
    priority            INT             NOT NULL DEFAULT 0 COMMENT '优先级（高值优先）',
    is_active           TINYINT(1)      NOT NULL DEFAULT 1,
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_category (category),
    INDEX idx_priority (priority DESC, hit_count DESC),
    INDEX idx_active (is_active),
    FULLTEXT INDEX ft_question (question) WITH PARSER ngram
                    COMMENT '中文全文索引，支持模糊匹配',
    FULLTEXT INDEX ft_answer (answer) WITH PARSER ngram
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='高频问答对（精确+语义双通道匹配）';


-- ============================================================================
-- 7. 校历事件表
-- 学期安排 / 考试时间 / 节假日
-- ============================================================================
CREATE TABLE calendar_events (
    id              INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    title           VARCHAR(200)    NOT NULL COMMENT '事件标题',
    event_type      ENUM('semester', 'exam', 'holiday', 'registration',
                         'activity', 'other')
                    NOT NULL DEFAULT 'other' COMMENT '事件类型',
    semester        VARCHAR(20)     NOT NULL COMMENT '所属学期',
    start_date      DATE            NOT NULL COMMENT '开始日期',
    end_date        DATE            NOT NULL COMMENT '结束日期',
    description     TEXT            DEFAULT NULL COMMENT '事件描述',
    location        VARCHAR(200)    DEFAULT NULL COMMENT '地点',
    is_holiday      TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '是否放假',
    is_active       TINYINT(1)      NOT NULL DEFAULT 1,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_semester (semester),
    INDEX idx_type (event_type),
    INDEX idx_date_range (start_date, end_date),
    INDEX idx_holiday (is_holiday)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='校历事件表';


-- ============================================================================
-- 8. 办事流程表
-- 分步流程指引，支持分支条件
-- ============================================================================
CREATE TABLE document_flows (
    id              INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    title           VARCHAR(200)    NOT NULL COMMENT '流程名称',
    flow_type       VARCHAR(50)     NOT NULL COMMENT '流程类型（leave/elect/scholarship/...）',
    department_id   INT UNSIGNED    DEFAULT NULL COMMENT '主管部门',
    description     TEXT            DEFAULT NULL COMMENT '流程简介',
    total_steps     TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '总步骤数',
    estimated_time  VARCHAR(100)    DEFAULT NULL COMMENT '预计办理时间',
    required_materials JSON         DEFAULT NULL COMMENT '所需材料清单',
    online_link     VARCHAR(500)    DEFAULT NULL COMMENT '在线办理链接',
    is_active       TINYINT(1)      NOT NULL DEFAULT 1,
    sort_order      INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '排序',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_flow_type (flow_type),
    INDEX idx_department (department_id),
    INDEX idx_active (is_active),
    CONSTRAINT fk_flow_dept FOREIGN KEY (department_id) REFERENCES departments(id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='办事流程主表';


-- ============================================================================
-- 9. 办事流程步骤表
-- 每个流程的详细步骤，支持条件分支
-- ============================================================================
CREATE TABLE flow_steps (
    id              INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    flow_id         INT UNSIGNED    NOT NULL COMMENT '所属流程',
    step_number     TINYINT UNSIGNED NOT NULL COMMENT '步骤序号',
    title           VARCHAR(200)    NOT NULL COMMENT '步骤标题',
    description     TEXT            NOT NULL COMMENT '步骤详细说明',
    department_id   INT UNSIGNED    DEFAULT NULL COMMENT '办理部门',
    location        VARCHAR(200)    DEFAULT NULL COMMENT '办理地点',
    phone           VARCHAR(30)     DEFAULT NULL COMMENT '联系电话',
    online_url      VARCHAR(500)    DEFAULT NULL COMMENT '在线办理链接',
    required_docs   JSON            DEFAULT NULL COMMENT '本步骤所需材料',
    estimated_time  VARCHAR(100)    DEFAULT NULL COMMENT '预计耗时',
    tips            TEXT            DEFAULT NULL COMMENT '注意事项/提示',
    condition_expr  VARCHAR(500)    DEFAULT NULL COMMENT '条件表达式（如适用人群过滤）',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uk_flow_step (flow_id, step_number),
    INDEX idx_department (department_id),
    CONSTRAINT fk_step_flow FOREIGN KEY (flow_id) REFERENCES document_flows(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_step_dept FOREIGN KEY (department_id) REFERENCES departments(id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='办事流程步骤明细表';


-- ============================================================================
-- 10. 对话会话表
-- 持久化对话历史
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
-- 11. 消息表
-- 单条对话消息
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
-- 12. 文档访问日志表
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


-- ============================================================================
-- 13. 系统配置表
-- 校园模块的动态配置项
-- ============================================================================
CREATE TABLE system_configs (
    id              INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    config_key      VARCHAR(100)    NOT NULL COMMENT '配置键',
    config_value    TEXT            NOT NULL COMMENT '配置值',
    description     VARCHAR(500)    DEFAULT NULL COMMENT '配置说明',
    is_public       TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '是否对外可见',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_config_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='系统动态配置表';


-- ============================================================================
-- 初始数据
-- ============================================================================

-- 插入默认部门根节点
INSERT INTO departments (id, name, code, parent_id, level, description) VALUES
(1, '全校', 'UNIV', NULL, 1, '全校根节点'),
(2, '教务处', 'ACAD', 1, 3, '教学管理与学籍管理'),
(3, '学生处（学工部）', 'STU', 1, 3, '学生事务管理'),
(4, '后勤管理处', 'LOG', 1, 3, '后勤保障服务'),
(5, '研究生院', 'GRAD', 1, 3, '研究生教育管理'),
(6, '国际交流处', 'INTL', 1, 3, '国际合作与交流'),
(7, '图书馆', 'LIB', 1, 3, '图书文献服务'),
(8, '信息技术中心', 'ITC', 1, 3, '校园网络与信息化'),
(9, '学生资助中心', 'SFA', 3, 3, '奖助学金与助学贷款'),
(10, '就业指导中心', 'CDC', 3, 3, '职业发展与就业指导');

-- 插入默认系统配置
INSERT INTO system_configs (config_key, config_value, description, is_public) VALUES
('campus.name', '示例大学', '学校名称', 1),
('campus.short_name', '示例大', '学校简称', 1),
('campus.logo_url', '/static/logo.png', '学校 Logo URL', 1),
('campus.address', '中国某市某区某路 100 号', '学校地址', 1),
('campus.semester.current', '2026春', '当前学期', 0),
('rag.chunk_size', '512', '文档切片默认大小', 0),
('rag.chunk_overlap', '64', '文档切片重叠大小', 0),
('rag.top_k', '5', '检索返回 Top-K 数量', 0),
('faq.cache_ttl', '3600', 'FAQ 缓存过期时间（秒）', 0),
('agent.max_iterations', '10', 'Agent 最大迭代次数', 0);
