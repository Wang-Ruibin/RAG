package com.campus.system.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.campus.system.domain.entity.SysUser;

import java.util.List;

/**
 * 用户 Service 接口
 */
public interface ISysUserService extends IService<SysUser> {

    /** 根据用户名查用户 */
    SysUser getByUserName(String userName);

    /** 查询用户权限列表 */
    List<String> getUserPermissions(String userName);

    /** 查询用户角色列表 */
    List<String> getUserRoles(String userName);

    /** 查询用户菜单（路由用） */
    List<com.campus.system.domain.entity.SysMenu> getUserMenus(String userName);

    /** 新增用户（含角色分配） */
    boolean addUser(SysUser user, List<Long> roleIds);

    /** 修改用户 */
    boolean updateUser(SysUser user, List<Long> roleIds);

    /** 重置密码 */
    boolean resetPassword(Long userId, String newPassword);

    /** 删除用户 */
    boolean deleteUsers(List<Long> userIds);

    /** 用户注册（默认普通角色） */
    void registerUser(String username, String password, String nickName, String email, String phone);
}
