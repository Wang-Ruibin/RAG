package com.campus.system.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.campus.common.core.exception.ServiceException;
import com.campus.system.domain.entity.SysRole;
import com.campus.system.mapper.SysRoleMapper;
import com.campus.system.mapper.SysRoleMenuMapper;
import com.campus.system.service.ISysRoleService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 角色 Service 实现
 */
@Service
public class SysRoleServiceImpl extends ServiceImpl<SysRoleMapper, SysRole> implements ISysRoleService {

    private final SysRoleMenuMapper roleMenuMapper;

    public SysRoleServiceImpl(SysRoleMenuMapper roleMenuMapper) {
        this.roleMenuMapper = roleMenuMapper;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean addRole(SysRole role, List<Long> menuIds) {
        if (this.count(new LambdaQueryWrapper<SysRole>()
                .eq(SysRole::getRoleKey, role.getRoleKey())
                .eq(SysRole::getDelFlag, "0")) > 0) {
            throw new ServiceException("角色标识「" + role.getRoleKey() + "」已存在");
        }
        role.setCreateTime(LocalDateTime.now());
        role.setUpdateTime(LocalDateTime.now());
        this.save(role);
        if (menuIds != null) {
            menuIds.forEach(mid -> roleMenuMapper.insertRoleMenu(role.getRoleId(), mid));
        }
        return true;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean updateRole(SysRole role, List<Long> menuIds) {
        role.setUpdateTime(LocalDateTime.now());
        this.updateById(role);
        if (menuIds != null) {
            roleMenuMapper.deleteByRoleId(role.getRoleId());
            menuIds.forEach(mid -> roleMenuMapper.insertRoleMenu(role.getRoleId(), mid));
        }
        return true;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean deleteRoles(List<Long> roleIds) {
        if (roleIds.contains(1L)) {
            throw new ServiceException("不可删除超级管理员角色");
        }
        roleIds.forEach(roleMenuMapper::deleteByRoleId);
        return this.removeByIds(roleIds);
    }

    @Override
    public List<Long> getRoleMenuIds(Long roleId) {
        return roleMenuMapper.selectMenuIdsByRoleId(roleId);
    }
}
