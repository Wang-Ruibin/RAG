package com.campus.system.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import cn.dev33.satoken.stp.StpUtil;
import cn.hutool.crypto.digest.BCrypt;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.campus.api.system.model.LoginUserVO;
import com.campus.common.core.domain.R;
import com.campus.common.core.web.PageQuery;
import com.campus.common.log.annotation.Log;
import com.campus.system.domain.entity.SysUser;
import com.campus.system.mapper.SysUserRoleMapper;
import com.campus.system.service.ISysUserService;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * 用户管理 Controller — 提供系统内部 CRUD + Feign 远程接口
 */
@RestController
@RequestMapping("/system/user")
public class SysUserController {

    private final ISysUserService userService;
    private final SysUserRoleMapper userRoleMapper;

    public SysUserController(ISysUserService userService, SysUserRoleMapper userRoleMapper) {
        this.userService = userService;
        this.userRoleMapper = userRoleMapper;
    }

    // ==================== 内部管理接口 ====================

    @SaCheckPermission("system:user:list")
    @GetMapping("/list")
    public R<PageQuery.PageResult<SysUser>> list(PageQuery pageQuery, SysUser user) {
        IPage<SysUser> page = userService.page(pageQuery.buildPage(),
                new LambdaQueryWrapper<SysUser>()
                        .like(user.getUserName() != null, SysUser::getUserName, user.getUserName())
                        .like(user.getNickName() != null, SysUser::getNickName, user.getNickName())
                        .like(user.getPhone() != null, SysUser::getPhone, user.getPhone())
                        .eq(user.getStatus() != null, SysUser::getStatus, user.getStatus())
                        .ne(SysUser::getUserId, 1L)
                        .orderByAsc(SysUser::getUserId));
        return R.ok(PageQuery.result(page));
    }

    @SaCheckPermission("system:user:add")
    @Log(title = "新增用户", businessType = 1)
    @PostMapping
    public R<Void> add(@RequestBody SysUser user, @RequestParam(required = false) List<Long> roleIds) {
        userService.addUser(user, roleIds);
        return R.ok();
    }

    @SaCheckPermission("system:user:edit")
    @Log(title = "修改用户", businessType = 2)
    @PutMapping
    public R<Void> edit(@RequestBody SysUser user, @RequestParam(required = false) List<Long> roleIds) {
        if (user.getUserId() == 1L) {
            return R.fail("不可修改超级管理员");
        }
        userService.updateUser(user, roleIds);
        return R.ok();
    }

    @SaCheckPermission("system:user:remove")
    @Log(title = "删除用户", businessType = 3)
    @DeleteMapping("/{userIds}")
    public R<Void> remove(@PathVariable("userIds") List<Long> userIds) {
        userService.deleteUsers(userIds);
        return R.ok();
    }

    @SaCheckPermission("system:user:resetPwd")
    @Log(title = "重置密码", businessType = 2)
    @PutMapping("/resetPwd")
    public R<Void> resetPwd(@RequestBody Map<String, Object> body) {
        Long userId = Long.valueOf(body.get("userId").toString());
        if (userId == 1L) {
            return R.fail("不可重置超级管理员密码");
        }
        String password = body.get("password").toString();
        userService.resetPassword(userId, password);
        return R.ok();
    }

    @GetMapping("/{userId}/roles")
    public R<List<Long>> getUserRoles(@PathVariable("userId") Long userId) {
        return R.ok(userRoleMapper.selectRoleIdsByUserId(userId));
    }

    // ==================== Feign 远程接口（Auth 模块调用） ====================

    @GetMapping("/info/{userName}")
    public R<LoginUserVO> getUserByName(@PathVariable("userName") String userName) {
        SysUser user = userService.getByUserName(userName);
        if (user == null) return R.fail("用户不存在");

        LoginUserVO vo = new LoginUserVO();
        vo.setUserId(user.getUserId());
        vo.setUserName(user.getUserName());
        vo.setNickName(user.getNickName());
        vo.setEmail(user.getEmail());
        vo.setPhone(user.getPhone());
        vo.setAvatar(user.getAvatar());
        vo.setStatus(user.getStatus());
        vo.setPermissions(userService.getUserPermissions(userName));
        vo.setRoles(userService.getUserRoles(userName));
        return R.ok(vo);
    }

    @GetMapping("/perms/{userName}")
    public R<List<String>> getUserPermissions(@PathVariable("userName") String userName) {
        return R.ok(userService.getUserPermissions(userName));
    }

    @GetMapping("/roles/{userName}")
    public R<List<String>> getUserRoles(@PathVariable("userName") String userName) {
        return R.ok(userService.getUserRoles(userName));
    }

    @GetMapping("/validate/{userName}")
    public R<Boolean> validatePassword(@PathVariable("userName") String userName,
                                        @RequestParam("password") String password) {
        SysUser user = userService.getByUserName(userName);
        if (user == null) return R.ok(false);
        return R.ok(BCrypt.checkpw(password, user.getPassword()));
    }

    /**
     * 用户注册（Feign 调用，默认分配普通角色）
     */
    @PostMapping("/register")
    public R<Void> register(@RequestParam("username") String username,
                            @RequestParam("password") String password,
                            @RequestParam("nickName") String nickName,
                            @RequestParam(value = "email", required = false) String email,
                            @RequestParam(value = "phone", required = false) String phone) {
        userService.registerUser(username, password, nickName, email, phone);
        return R.ok();
    }

    @GetMapping("/routers")
    public R<List<com.campus.system.domain.entity.SysMenu>> getRouters() {
        String userName = StpUtil.getLoginIdAsString();
        return R.ok(userService.getUserMenus(userName));
    }
}
