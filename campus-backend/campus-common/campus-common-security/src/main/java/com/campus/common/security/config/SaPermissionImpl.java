package com.campus.common.security.config;

import cn.dev33.satoken.session.SaSession;
import cn.dev33.satoken.stp.StpInterface;
import cn.dev33.satoken.stp.StpUtil;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Collections;
import java.util.List;

/**
 * Sa-Token 权限/角色解析实现 — 从 TokenSession (Redis) 读取
 * <p>
 * 权限数据由 Auth 模块在登录时写入 TokenSession，
 * 各业务模块通过本实现读取，无需跨服务 Feign 调用。
 *
 * @author CampusQA Team
 */
public class SaPermissionImpl implements StpInterface {

    private static final Logger log = LoggerFactory.getLogger(SaPermissionImpl.class);

    @Override
    public List<String> getPermissionList(Object loginId, String loginType) {
        try {
            SaSession userSession = StpUtil.getSessionByLoginId(loginId);
            if (userSession == null) {
                return Collections.emptyList();
            }
            @SuppressWarnings("unchecked")
            List<String> perms = (List<String>) userSession.get("permissions");
            return perms != null ? perms : Collections.emptyList();
        } catch (Exception e) {
            log.warn("获取用户权限列表失败, loginId={}, error={}", loginId, e.getMessage());
            return Collections.emptyList();
        }
    }

    @Override
    public List<String> getRoleList(Object loginId, String loginType) {
        try {
            SaSession userSession = StpUtil.getSessionByLoginId(loginId);
            if (userSession == null) {
                return Collections.emptyList();
            }
            @SuppressWarnings("unchecked")
            List<String> roles = (List<String>) userSession.get("roles");
            return roles != null ? roles : Collections.emptyList();
        } catch (Exception e) {
            log.warn("获取用户角色列表失败, loginId={}, error={}", loginId, e.getMessage());
            return Collections.emptyList();
        }
    }
}
