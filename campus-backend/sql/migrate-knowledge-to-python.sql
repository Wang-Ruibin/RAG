-- ============================================
-- CampusQA 知识库模块菜单迁移 SQL
-- Java campus-knowledge 退役 → Python /api/documents
-- 执行前确认数据库是 campus_qa
-- ============================================

-- 1. 清理分类管理相关的角色-菜单关联
DELETE FROM sys_role_menu WHERE menu_id IN (20, 2001, 2002, 2003, 2004, 2005);

-- 2. 删除分类管理菜单及按钮权限
DELETE FROM sys_menu WHERE menu_id IN (20, 2001, 2002, 2003, 2004, 2005);

-- 3. 删除废弃的文档按钮（导出/导入/检索 —— Python 不支持）
DELETE FROM sys_role_menu WHERE menu_id IN (2104, 2105, 2107);
DELETE FROM sys_menu WHERE menu_id IN (2104, 2105, 2107);

-- 4. 文档管理 → 知识库管理（名称对齐 Python）
UPDATE sys_menu SET menu_name = '知识库管理' WHERE menu_id = 21;

-- 5. 文档新增 → 文档上传（Python 是文件上传模式）
UPDATE sys_menu SET menu_name = '文档上传', perms = 'knowledge:document:upload' WHERE menu_id = 2101;

-- 6. 新增「文档索引」按钮权限（Python reindex）
INSERT INTO sys_menu (menu_id, menu_name, parent_id, order_num, path, component, menu_type, perms, icon, status, visible)
VALUES (2108, '文档索引', 21, 8, NULL, NULL, 'F', 'knowledge:document:reindex', NULL, '1', '1');

-- 7. 普通用户(role_id=2)赋权更新
DELETE FROM sys_role_menu WHERE role_id = 2 AND menu_id IN (20, 2004);
INSERT INTO sys_role_menu (role_id, menu_id) VALUES (2, 2108);

-- 8. 清理旧知识分类/文档表（Python 有自己的表）
DROP TABLE IF EXISTS campus_knowledge_document;
DROP TABLE IF EXISTS campus_knowledge_category;
