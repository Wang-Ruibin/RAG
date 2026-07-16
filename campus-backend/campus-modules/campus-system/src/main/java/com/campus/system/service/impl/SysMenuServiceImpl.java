package com.campus.system.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.campus.system.domain.entity.SysMenu;
import com.campus.system.mapper.SysMenuMapper;
import com.campus.system.mapper.SysRoleMenuMapper;
import com.campus.system.service.ISysMenuService;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

/**
 * 菜单 Service 实现
 */
@Service
public class SysMenuServiceImpl extends ServiceImpl<SysMenuMapper, SysMenu> implements ISysMenuService {

    private final SysRoleMenuMapper roleMenuMapper;

    public SysMenuServiceImpl(SysRoleMenuMapper roleMenuMapper) {
        this.roleMenuMapper = roleMenuMapper;
    }

    @Override
    public List<SysMenu> getMenuTree() {
        List<SysMenu> allMenus = this.list(new LambdaQueryWrapper<SysMenu>()
                .eq(SysMenu::getStatus, "1")
                .orderByAsc(SysMenu::getOrderNum));
        return buildTree(allMenus, 0L);
    }

    @Override
    public List<SysMenu> getMenuTreeByRoleId(Long roleId) {
        List<Long> menuIds = roleMenuMapper.selectMenuIdsByRoleId(roleId);
        List<SysMenu> allMenus = this.list(new LambdaQueryWrapper<SysMenu>()
                .eq(SysMenu::getStatus, "1")
                .orderByAsc(SysMenu::getOrderNum));
        // 标记选中状态
        allMenus.forEach(m -> m.setRemark(menuIds.contains(m.getMenuId()) ? "checked" : ""));
        return buildTree(allMenus, 0L);
    }

    private List<SysMenu> buildTree(List<SysMenu> menus, Long parentId) {
        List<SysMenu> tree = new ArrayList<>();
        for (SysMenu menu : menus) {
            if (menu.getParentId().equals(parentId)) {
                List<SysMenu> children = buildTree(menus, menu.getMenuId());
                menu.setChildren(children.isEmpty() ? null : children);
                tree.add(menu);
            }
        }
        return tree;
    }
}
