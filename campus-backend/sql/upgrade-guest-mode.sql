-- ==================== 访客模式增量脚本（已有库执行） ====================
-- 新库不需要本脚本：init.sql 已包含全部访客数据。
--
-- 执行前预检：下面的查询必须返回空！
-- 若已有人注册占用了 guest 用户名，先人工处理（改名该用户），再执行本脚本，
-- 防止把访客角色绑到人类账号上。
--
--   SELECT user_id, nick_name, create_time FROM sys_user WHERE user_name = 'guest';
--
-- 本脚本刻意使用裸 INSERT（不带 WHERE NOT EXISTS）：
-- 若 guest / role_key='guest' 已被占用，唯一键冲突会让脚本响亮失败，而不是静默跳过。

USE campus_qa;

-- 访客账号（仅经 /auth/guest-login 免密进入；密码为随机串的 BCrypt，明文已丢弃，且 Java 侧禁止其密码登录）
-- 不指定主键，避开已有自增值
INSERT INTO sys_user (user_name, nick_name, password, status, remark)
VALUES ('guest', '访客用户', '$2a$10$BOvua01//uwR6Ox/5lAVnemqLEqHvcU.2kJPtCTBF8NQSeAxhjHqe', '1',
        '系统内置访客账号，免验证码免密码，仅限智能问答，停用即关闭访客通道');

-- 访客角色
INSERT INTO sys_role (role_name, role_key, role_sort, status, remark)
VALUES ('访客', 'guest', 3, '1', '访客角色，仅首页智能问答，问答不留痕');

-- 绑定用户-角色（按 user_name/role_key 关联，不依赖具体主键值）
INSERT INTO sys_user_role (user_id, role_id)
SELECT u.user_id, r.role_id
FROM sys_user u
JOIN sys_role r ON u.user_name = 'guest' AND r.role_key = 'guest';

-- 访客赋权（仅首页智能问答 menu_id=1）
INSERT INTO sys_role_menu (role_id, menu_id)
SELECT r.role_id, 1 FROM sys_role r WHERE r.role_key = 'guest';
