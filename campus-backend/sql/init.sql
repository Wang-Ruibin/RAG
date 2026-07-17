-- ============================================================
-- CampusQA - 校园知识问答助手 数据库初始化
-- 执行方式: docker exec -i campus-mysql mysql -uroot -p123456 campus_qa < init.sql
-- ============================================================

-- 创建数据库（如果还没创建）
CREATE DATABASE IF NOT EXISTS campus_qa DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE campus_qa;

-- ==================== 系统管理表 ====================

-- 用户表
DROP TABLE IF EXISTS sys_user;
CREATE TABLE sys_user (
    user_id         BIGINT          NOT NULL AUTO_INCREMENT  COMMENT '用户ID',
    user_name       VARCHAR(64)     NOT NULL                COMMENT '用户名（工号/学号）',
    nick_name       VARCHAR(64)     NOT NULL                COMMENT '昵称',
    password        VARCHAR(255)    NOT NULL                COMMENT '密码（BCrypt加密）',
    email           VARCHAR(128)    DEFAULT NULL            COMMENT '邮箱',
    phone           VARCHAR(20)     DEFAULT NULL            COMMENT '手机号',
    sex             CHAR(1)         DEFAULT '0'             COMMENT '性别(0未知 1男 2女)',
    avatar          VARCHAR(255)    DEFAULT NULL            COMMENT '头像URL',
    status          CHAR(1)         DEFAULT '1'             COMMENT '状态(0停用 1正常)',
    login_ip        VARCHAR(128)    DEFAULT NULL            COMMENT '最后登录IP',
    login_date      DATETIME        DEFAULT NULL            COMMENT '最后登录时间',
    create_by       VARCHAR(64)     DEFAULT NULL            COMMENT '创建者',
    create_time     DATETIME        DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_by       VARCHAR(64)     DEFAULT NULL            COMMENT '更新者',
    update_time     DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    del_flag        CHAR(1)         DEFAULT '0'             COMMENT '删除标志(0正常 1删除)',
    remark          VARCHAR(500)    DEFAULT NULL            COMMENT '备注',
    PRIMARY KEY (user_id),
    UNIQUE KEY uk_user_name (user_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 角色表
DROP TABLE IF EXISTS sys_role;
CREATE TABLE sys_role (
    role_id         BIGINT          NOT NULL AUTO_INCREMENT  COMMENT '角色ID',
    role_name       VARCHAR(64)     NOT NULL                COMMENT '角色名称',
    role_key        VARCHAR(64)     NOT NULL                COMMENT '角色权限标识',
    role_sort       INT             DEFAULT 0               COMMENT '排序',
    status          CHAR(1)         DEFAULT '1'             COMMENT '状态(0停用 1正常)',
    create_by       VARCHAR(64)     DEFAULT NULL            COMMENT '创建者',
    create_time     DATETIME        DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_by       VARCHAR(64)     DEFAULT NULL            COMMENT '更新者',
    update_time     DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    del_flag        CHAR(1)         DEFAULT '0'             COMMENT '删除标志',
    remark          VARCHAR(500)    DEFAULT NULL            COMMENT '备注',
    PRIMARY KEY (role_id),
    UNIQUE KEY uk_role_key (role_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色表';

-- 菜单表
DROP TABLE IF EXISTS sys_menu;
CREATE TABLE sys_menu (
    menu_id         BIGINT          NOT NULL AUTO_INCREMENT  COMMENT '菜单ID',
    menu_name       VARCHAR(64)     NOT NULL                COMMENT '菜单名称',
    parent_id       BIGINT          DEFAULT 0               COMMENT '父菜单ID',
    order_num       INT             DEFAULT 0               COMMENT '排序',
    path            VARCHAR(255)    DEFAULT NULL            COMMENT '路由地址',
    component       VARCHAR(255)    DEFAULT NULL            COMMENT '组件路径',
    query           VARCHAR(255)    DEFAULT NULL            COMMENT '路由参数',
    route_name      VARCHAR(64)     DEFAULT NULL            COMMENT '路由名称',
    is_frame        CHAR(1)         DEFAULT '0'             COMMENT '是否外链',
    is_cache        CHAR(1)         DEFAULT '0'             COMMENT '是否缓存',
    menu_type       CHAR(1)         NOT NULL                COMMENT '菜单类型(M目录 C菜单 F按钮)',
    visible         CHAR(1)         DEFAULT '1'             COMMENT '是否显示',
    status          CHAR(1)         DEFAULT '1'             COMMENT '状态',
    perms           VARCHAR(255)    DEFAULT NULL            COMMENT '权限标识',
    icon            VARCHAR(128)    DEFAULT NULL            COMMENT '菜单图标',
    create_by       VARCHAR(64)     DEFAULT NULL            COMMENT '创建者',
    create_time     DATETIME        DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_by       VARCHAR(64)     DEFAULT NULL            COMMENT '更新者',
    update_time     DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    remark          VARCHAR(500)    DEFAULT NULL            COMMENT '备注',
    PRIMARY KEY (menu_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='菜单表';

-- 用户角色关联表
DROP TABLE IF EXISTS sys_user_role;
CREATE TABLE sys_user_role (
    user_id         BIGINT          NOT NULL                COMMENT '用户ID',
    role_id         BIGINT          NOT NULL                COMMENT '角色ID',
    PRIMARY KEY (user_id, role_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户角色关联表';

-- 角色菜单关联表
DROP TABLE IF EXISTS sys_role_menu;
CREATE TABLE sys_role_menu (
    role_id         BIGINT          NOT NULL                COMMENT '角色ID',
    menu_id         BIGINT          NOT NULL                COMMENT '菜单ID',
    PRIMARY KEY (role_id, menu_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色菜单关联表';

-- 操作日志表
DROP TABLE IF EXISTS sys_oper_log;
CREATE TABLE sys_oper_log (
    oper_id         BIGINT          NOT NULL AUTO_INCREMENT  COMMENT '日志ID',
    title           VARCHAR(128)    DEFAULT NULL            COMMENT '操作模块',
    business_type   INT             DEFAULT 0               COMMENT '业务类型(0其它 1新增 2修改 3删除)',
    method          VARCHAR(255)    DEFAULT NULL            COMMENT '请求方法',
    request_method  VARCHAR(10)     DEFAULT NULL            COMMENT '请求方式(GET/POST)',
    oper_url        VARCHAR(255)    DEFAULT NULL            COMMENT '请求URL',
    oper_ip         VARCHAR(128)    DEFAULT NULL            COMMENT '操作IP',
    oper_param      TEXT            DEFAULT NULL            COMMENT '请求参数',
    json_result     TEXT            DEFAULT NULL            COMMENT '返回结果',
    status          INT             DEFAULT 1               COMMENT '状态(0异常 1正常)',
    error_msg       TEXT            DEFAULT NULL            COMMENT '错误信息',
    oper_time       DATETIME        DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
    oper_name       VARCHAR(64)     DEFAULT NULL            COMMENT '操作人',
    cost_time       BIGINT          DEFAULT 0               COMMENT '耗时(ms)',
    PRIMARY KEY (oper_id),
    KEY idx_oper_time (oper_time),
    KEY idx_oper_name (oper_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='操作日志表';

-- 登录日志表
DROP TABLE IF EXISTS sys_login_info;
CREATE TABLE sys_login_info (
    info_id         BIGINT          NOT NULL AUTO_INCREMENT  COMMENT '日志ID',
    user_name       VARCHAR(64)     DEFAULT NULL            COMMENT '用户名',
    ipaddr          VARCHAR(128)    DEFAULT NULL            COMMENT '登录IP',
    status          CHAR(1)         DEFAULT '1'             COMMENT '状态(0失败 1成功)',
    msg             VARCHAR(255)    DEFAULT NULL            COMMENT '提示信息',
    login_time      DATETIME        DEFAULT CURRENT_TIMESTAMP COMMENT '登录时间',
    PRIMARY KEY (info_id),
    KEY idx_login_time (login_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='登录日志表';

-- ==================== 初始数据 ====================
-- 注：知识库文档管理已迁移至 Python RAG 后端（documents 等表由 alembic 管理），
--     原 campus_knowledge_category / campus_knowledge_document 表已退役删除。

-- 管理员账号 admin / admin123
INSERT INTO sys_user (user_id, user_name, nick_name, password, status, remark) VALUES
(1, 'admin', '超级管理员', '$2a$10$7JB720yubVSZvUI0rEqK/.VqGOZTH.ulu33dHOiBE8ByOhJIrdAu2', '1', '系统内置超级管理员');

-- 角色
INSERT INTO sys_role (role_id, role_name, role_key, role_sort, status, remark) VALUES
(1, '超级管理员', 'admin', 1, '1', '系统内置角色，拥有所有权限'),
(2, '普通用户', 'user', 2, '1', '普通用户角色');

-- 管理员绑定角色
INSERT INTO sys_user_role (user_id, role_id) VALUES (1, 1);

-- 菜单数据
INSERT INTO sys_menu (menu_id, menu_name, parent_id, order_num, path, component, menu_type, perms, icon, visible, status) VALUES
-- 一级目录
(1,  '首页',      0, 1, '/home',        'home/index',      'C', 'home:view',    'home',       '1', '1'),
(2,  '知识库管理', 0, 2, '/knowledge',   NULL,              'M', NULL,           'document',   '1', '1'),
(3,  '系统管理',   0, 3, '/system',      NULL,              'M', NULL,           'setting',    '1', '1'),
-- 知识库子菜单
(21, '文档管理',   2, 2, '/knowledge/document', 'knowledge/document/index', 'C', 'knowledge:document:list',   'document','1', '1'),
(22, '纠错审核',   2, 3, '/knowledge/correction', 'knowledge/correction/index', 'C', 'knowledge:correction:review', 'EditPen', '1', '1'),
-- 系统管理子菜单
(30, '用户管理',   3, 1, '/system/user', 'system/user/index',       'C', 'system:user:list',   'user',    '1', '1'),
(31, '角色管理',   3, 2, '/system/role', 'system/role/index',       'C', 'system:role:list',   'Avatar',  '1', '1'),
(32, '系统日志',   3, 3, '/system/log',  'system/log/index',        'C', 'system:log:list',    'Tickets', '1', '1'),
-- 知识库按钮权限（文档管理走 Python RAG 后端，无导出/导入/检索）
(2101, '文档上传',  21, 1, NULL, NULL, 'F', 'knowledge:document:upload',  NULL, '1', '1'),
(2102, '文档编辑',  21, 2, NULL, NULL, 'F', 'knowledge:document:edit',    NULL, '1', '1'),
(2103, '文档删除',  21, 3, NULL, NULL, 'F', 'knowledge:document:remove',  NULL, '1', '1'),
(2106, '文档查询',  21, 6, NULL, NULL, 'F', 'knowledge:document:query',   NULL, '1', '1'),
(2108, '文档索引',  21, 8, NULL, NULL, 'F', 'knowledge:document:reindex', NULL, '1', '1'),
-- 系统管理按钮权限
(3001, '用户新增',  30, 1, NULL, NULL, 'F', 'system:user:add',    NULL, '1', '1'),
(3002, '用户编辑',  30, 2, NULL, NULL, 'F', 'system:user:edit',   NULL, '1', '1'),
(3003, '用户删除',  30, 3, NULL, NULL, 'F', 'system:user:remove', NULL, '1', '1'),
(3004, '用户重置密码',30,4, NULL, NULL, 'F', 'system:user:resetPwd', NULL,'1', '1'),
(3005, '用户查询',  30, 5, NULL, NULL, 'F', 'system:user:query',  NULL, '1', '1'),
(3006, '用户启停',  30, 6, NULL, NULL, 'F', 'system:user:status', NULL, '1', '1'),
(3007, '用户导出',  30, 7, NULL, NULL, 'F', 'system:user:export', NULL, '1', '1'),
(3101, '角色新增',  31, 1, NULL, NULL, 'F', 'system:role:add',    NULL, '1', '1'),
(3102, '角色编辑',  31, 2, NULL, NULL, 'F', 'system:role:edit',   NULL, '1', '1'),
(3103, '角色删除',  31, 3, NULL, NULL, 'F', 'system:role:remove', NULL, '1', '1'),
(3104, '角色查询',  31, 4, NULL, NULL, 'F', 'system:role:query',  NULL, '1', '1'),
(3105, '角色导出',  31, 5, NULL, NULL, 'F', 'system:role:export', NULL, '1', '1'),
(3201, '日志查看',  32, 1, NULL, NULL, 'F', 'system:log:query',   NULL, '1', '1'),
(3202, '日志删除',  32, 2, NULL, NULL, 'F', 'system:log:remove',  NULL, '1', '1'),
(3203, '日志列表',  32, 3, NULL, NULL, 'F', 'system:log:list',   NULL, '1', '1'),
(3204, '日志导出',  32, 4, NULL, NULL, 'F', 'system:log:export', NULL, '1', '1'),
(3205, '日志详情',  32, 5, NULL, NULL, 'F', 'system:log:detail', NULL, '1', '1');

-- 管理员角色赋权（所有菜单）
INSERT INTO sys_role_menu (role_id, menu_id)
SELECT 1, menu_id FROM sys_menu;

-- 普通用户赋权（首页；文档管理为管理员专属，走 Python 侧 ADMIN 校验）
INSERT INTO sys_role_menu (role_id, menu_id) VALUES
(2, 1);

-- Nacos 配置库（Nacos自身使用）
CREATE DATABASE IF NOT EXISTS nacos_config DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
