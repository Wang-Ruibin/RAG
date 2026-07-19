package com.campus.system.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.campus.system.domain.entity.SysMenu;

import java.util.List;

/**
 * 菜单 Service 接口
 */
public interface ISysMenuService extends IService<SysMenu> {

    /** 获取菜单树 */
    List<SysMenu> getMenuTree();

    /** 根据角色ID获取菜单树 */
    List<SysMenu> getMenuTreeByRoleId(Long roleId);
}
