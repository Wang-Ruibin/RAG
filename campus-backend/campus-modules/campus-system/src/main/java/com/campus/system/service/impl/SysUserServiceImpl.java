package com.campus.system.service.impl;

import cn.hutool.crypto.digest.BCrypt;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.campus.common.core.exception.ServiceException;
import com.campus.system.domain.entity.SysMenu;
import com.campus.system.domain.entity.SysUser;
import com.campus.system.mapper.SysMenuMapper;
import com.campus.system.mapper.SysUserMapper;
import com.campus.system.mapper.SysUserRoleMapper;
import com.campus.system.service.ISysUserService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * 用户 Service 实现
 */
@Service
public class SysUserServiceImpl extends ServiceImpl<SysUserMapper, SysUser> implements ISysUserService {

    private final SysUserRoleMapper userRoleMapper;
    private final SysMenuMapper menuMapper;

    public SysUserServiceImpl(SysUserRoleMapper userRoleMapper, SysMenuMapper menuMapper) {
        this.userRoleMapper = userRoleMapper;
        this.menuMapper = menuMapper;
    }

    @Override
    public SysUser getByUserName(String userName) {
        return this.getOne(new LambdaQueryWrapper<SysUser>()
                .eq(SysUser::getUserName, userName));
    }

    @Override
    public List<String> getUserPermissions(String userName) {
        SysUser user = getByUserName(userName);
        if (user == null) return List.of();
        return baseMapper.selectPermsByUserId(user.getUserId());
    }

    @Override
    public List<String> getUserRoles(String userName) {
        SysUser user = getByUserName(userName);
        if (user == null) return List.of();
        return baseMapper.selectRolesByUserId(user.getUserId());
    }

    @Override
    public List<SysMenu> getUserMenus(String userName) {
        SysUser user = getByUserName(userName);
        if (user == null) return List.of();
        List<SysMenu> flatList = new ArrayList<>(baseMapper.selectMenusByUserId(user.getUserId()));
        // 逐级向上补全父级菜单，避免子菜单因父级缺失而成孤儿
        Set<Long> existingIds = new HashSet<>();
        for (SysMenu m : flatList) existingIds.add(m.getMenuId());
        Set<Long> missing = new HashSet<>();
        for (SysMenu m : flatList) {
            if (m.getParentId() != 0 && !existingIds.contains(m.getParentId())) {
                missing.add(m.getParentId());
            }
        }
        while (!missing.isEmpty()) {
            List<SysMenu> parents = menuMapper.selectBatchIds(missing);
            flatList.addAll(parents);
            existingIds.addAll(missing);
            missing.clear();
            for (SysMenu p : parents) {
                if (p.getParentId() != 0 && !existingIds.contains(p.getParentId())) {
                    missing.add(p.getParentId());
                }
            }
        }
        return buildTree(flatList, 0L);
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

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean addUser(SysUser user, List<Long> roleIds) {
        // 用户名唯一校验
        if (this.getByUserName(user.getUserName()) != null) {
            throw new ServiceException("用户名已存在");
        }
        // 密码加密
        user.setPassword(BCrypt.hashpw(user.getPassword()));
        this.save(user);
        // 分配角色
        if (roleIds != null) {
            roleIds.forEach(rid -> userRoleMapper.insertUserRole(user.getUserId(), rid));
        }
        return true;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean updateUser(SysUser user, List<Long> roleIds) {
        SysUser dbUser = this.getById(user.getUserId());
        if (dbUser == null) throw new ServiceException("用户不存在");
        // 密码不更新
        user.setPassword(null);
        this.updateById(user);
        // 重新分配角色
        if (roleIds != null) {
            userRoleMapper.deleteByUserId(user.getUserId());
            roleIds.forEach(rid -> userRoleMapper.insertUserRole(user.getUserId(), rid));
        }
        return true;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean resetPassword(Long userId, String newPassword) {
        SysUser user = new SysUser();
        user.setUserId(userId);
        user.setPassword(BCrypt.hashpw(newPassword));
        return this.updateById(user);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean deleteUsers(List<Long> userIds) {
        if (userIds.contains(1L)) {
            throw new ServiceException("不可删除超级管理员");
        }
        // 清理角色关联
        userIds.forEach(userRoleMapper::deleteByUserId);
        return this.removeByIds(userIds);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void registerUser(String username, String password, String nickName,
                              String email, String phone) {
        if (this.getByUserName(username) != null) {
            throw new ServiceException("用户名已存在");
        }
        SysUser user = new SysUser();
        user.setUserName(username);
        user.setPassword(BCrypt.hashpw(password));
        user.setNickName(nickName);
        user.setEmail(email);
        user.setPhone(phone);
        user.setStatus("1");
        user.setDelFlag("0");
        this.save(user);
        // 分配普通角色 role_id=2
        userRoleMapper.insertUserRole(user.getUserId(), 2L);
    }
}
