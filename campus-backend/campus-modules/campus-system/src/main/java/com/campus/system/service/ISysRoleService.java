package com.campus.system.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.campus.system.domain.entity.SysRole;

import java.util.List;

/**
 * 角色 Service 接口
 */
public interface ISysRoleService extends IService<SysRole> {

    /** 新增角色（含菜单分配） */
    boolean addRole(SysRole role, List<Long> menuIds);

    /** 修改角色 */
    boolean updateRole(SysRole role, List<Long> menuIds);

    /** 删除角色 */
    boolean deleteRoles(List<Long> roleIds);

    /** 获取角色关联的菜单ID */
    List<Long> getRoleMenuIds(Long roleId);
}
