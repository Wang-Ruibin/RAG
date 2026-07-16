package com.campus.system.controller;

import com.campus.common.core.domain.R;
import com.campus.system.domain.entity.SysMenu;
import com.campus.system.service.ISysMenuService;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 菜单管理 Controller
 */
@RestController
@RequestMapping("/system/menu")
public class SysMenuController {

    private final ISysMenuService menuService;

    public SysMenuController(ISysMenuService menuService) {
        this.menuService = menuService;
    }

    @GetMapping("/tree")
    public R<List<SysMenu>> tree() {
        return R.ok(menuService.getMenuTree());
    }

    @GetMapping("/tree/{roleId}")
    public R<List<SysMenu>> treeByRole(@PathVariable("roleId") Long roleId) {
        return R.ok(menuService.getMenuTreeByRoleId(roleId));
    }

    @GetMapping("/list")
    public R<List<SysMenu>> list() {
        return R.ok(menuService.list());
    }
}
