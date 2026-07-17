package com.campus.system.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.campus.common.core.domain.R;
import com.campus.common.core.web.PageQuery;
import com.campus.common.log.annotation.Log;
import com.campus.system.domain.entity.SysRole;
import com.campus.system.service.ISysRoleService;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 角色管理 Controller
 */
@RestController
@RequestMapping("/system/role")
public class SysRoleController {

    private final ISysRoleService roleService;

    public SysRoleController(ISysRoleService roleService) {
        this.roleService = roleService;
    }

    @SaCheckPermission("system:role:list")
    @GetMapping("/list")
    public R<PageQuery.PageResult<SysRole>> list(PageQuery pageQuery, SysRole role) {
        IPage<SysRole> page = roleService.page(pageQuery.buildPage(),
                new LambdaQueryWrapper<SysRole>()
                        .like(role.getRoleName() != null, SysRole::getRoleName, role.getRoleName())
                        .like(role.getRoleKey() != null, SysRole::getRoleKey, role.getRoleKey())
                        .eq(role.getStatus() != null, SysRole::getStatus, role.getStatus())
                        .orderByAsc(SysRole::getRoleSort));
        return R.ok(PageQuery.result(page));
    }

    @SaCheckPermission("system:role:add")
    @Log(title = "新增角色", businessType = 1)
    @PostMapping
    public R<Void> add(@RequestBody SysRole role, @RequestParam(required = false) List<Long> menuIds) {
        roleService.addRole(role, menuIds);
        return R.ok();
    }

    @SaCheckPermission("system:role:edit")
    @Log(title = "修改角色", businessType = 2)
    @PutMapping
    public R<Void> edit(@RequestBody SysRole role, @RequestParam(required = false) List<Long> menuIds) {
        if (role.getRoleId() == 1L) {
            return R.fail("不可修改超级管理员角色");
        }
        roleService.updateRole(role, menuIds);
        return R.ok();
    }

    @SaCheckPermission("system:role:remove")
    @Log(title = "删除角色", businessType = 3)
    @DeleteMapping("/{roleIds}")
    public R<Void> remove(@PathVariable("roleIds") List<Long> roleIds) {
        roleService.deleteRoles(roleIds);
        return R.ok();
    }

    @GetMapping("/{roleId}/menus")
    public R<List<Long>> getRoleMenus(@PathVariable("roleId") Long roleId) {
        return R.ok(roleService.getRoleMenuIds(roleId));
    }
}
