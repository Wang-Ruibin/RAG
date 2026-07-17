package com.campus.system.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.campus.system.domain.entity.SysUser;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * 用户 Mapper
 */
public interface SysUserMapper extends BaseMapper<SysUser> {

    @Select("SELECT DISTINCT m.perms FROM sys_menu m " +
            "INNER JOIN sys_role_menu rm ON m.menu_id = rm.menu_id " +
            "INNER JOIN sys_user_role ur ON rm.role_id = ur.role_id " +
            "WHERE ur.user_id = #{userId} AND m.perms IS NOT NULL AND m.perms != ''")
    List<String> selectPermsByUserId(@Param("userId") Long userId);

    @Select("SELECT DISTINCT r.role_key FROM sys_role r " +
            "INNER JOIN sys_user_role ur ON r.role_id = ur.role_id " +
            "WHERE ur.user_id = #{userId}")
    List<String> selectRolesByUserId(@Param("userId") Long userId);

    @Select("SELECT DISTINCT m.* FROM sys_menu m " +
            "INNER JOIN sys_role_menu rm ON m.menu_id = rm.menu_id " +
            "INNER JOIN sys_user_role ur ON rm.role_id = ur.role_id " +
            "WHERE ur.user_id = #{userId} AND m.menu_type IN ('M','C') AND m.status = '1' " +
            "ORDER BY m.order_num")
    List<com.campus.system.domain.entity.SysMenu> selectMenusByUserId(@Param("userId") Long userId);
}
