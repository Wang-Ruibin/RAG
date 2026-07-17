package com.campus.auth.service;

import cn.dev33.satoken.stp.SaTokenInfo;
import cn.dev33.satoken.stp.StpUtil;
import com.campus.api.system.RemoteUserService;
import com.campus.api.system.model.LoginUserVO;
import com.campus.common.core.domain.R;
import com.campus.common.core.exception.ServiceException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 登录业务逻辑
 *
 * @author CampusQA Team
 */
@Service
public class LoginService {

    private static final Logger log = LoggerFactory.getLogger(LoginService.class);

    private final RemoteUserService remoteUserService;

    public LoginService(RemoteUserService remoteUserService) {
        this.remoteUserService = remoteUserService;
    }

    /**
     * 用户名+密码登录
     */
    public SaTokenInfo login(String username, String password) {
        // 1. 通过 Feign 调用 System 服务查询用户
        R<LoginUserVO> result = remoteUserService.getUserByName(username);

        if (result == null || !result.isSuccess() || result.getData() == null) {
            throw new ServiceException("用户不存在");
        }

        LoginUserVO user = result.getData();

        // 2. 校验状态
        if (!"1".equals(user.getStatus())) {
            throw new ServiceException("账号已被停用，请联系管理员");
        }

        // 3. 校验密码（BCrypt）
        if (!checkPassword(password, username)) {
            // 实际应从 System 服务获取加密密码比对
            // 这里通过 Feign 接口间接校验
            throw new ServiceException("密码错误");
        }

        // 4. 登录 Sa-Token
        StpUtil.login(user.getUserName());

        // 5. 缓存用户信息 + 权限/角色到 TokenSession（供各服务 StpInterface 鉴权）
        StpUtil.getSession().set("userInfo", user);
        StpUtil.getSession().set("permissions", user.getPermissions());
        StpUtil.getSession().set("roles", user.getRoles());

        // 6. 获取 Token 信息
        SaTokenInfo tokenInfo = StpUtil.getTokenInfo();
        log.info("用户登录成功: {}", username);
        return tokenInfo;
    }

    /**
     * 用户注册
     */
    public void register(String username, String password, String nickName, String email, String phone) {
        R<LoginUserVO> result = remoteUserService.getUserByName(username);
        if (result != null && result.isSuccess() && result.getData() != null) {
            throw new ServiceException("用户名已存在");
        }
        R<Void> reg = remoteUserService.registerUser(username, password, nickName, email, phone);
        if (reg == null || !reg.isSuccess()) {
            throw new ServiceException(reg != null ? reg.getMsg() : "注册失败");
        }
    }

    /**
     * 登出
     */
    public void logout() {
        try {
            StpUtil.logout();
        } catch (Exception e) {
            log.warn("登出异常: {}", e.getMessage());
        }
    }

    /**
     * 获取当前用户信息
     */
    public Map<String, Object> getCurrentUserInfo() {
        String username = StpUtil.getLoginIdAsString();

        // 从 Session 缓存获取
        LoginUserVO user = (LoginUserVO) StpUtil.getSession().get("userInfo");
        if (user == null) {
            // 缓存过期，从 System 服务重新加载
            R<LoginUserVO> result = remoteUserService.getUserByName(username);
            if (result != null && result.isSuccess()) {
                user = result.getData();
                StpUtil.getSession().set("userInfo", user);
            }
        }

        R<List<String>> permsResult = remoteUserService.getUserPermissions(username);
        R<List<String>> rolesResult = remoteUserService.getUserRoles(username);

        Map<String, Object> info = new HashMap<>();
        info.put("user", user != null ? user : Map.of("userName", username));
        info.put("permissions", permsResult != null && permsResult.isSuccess() ? permsResult.getData() : List.of());
        info.put("roles", rolesResult != null && rolesResult.isSuccess() ? rolesResult.getData() : List.of());
        return info;
    }

    /**
     * 密码校验（通过 Feign 调用 System 服务 BCrypt 比对）
     */
    private boolean checkPassword(String rawPassword, String username) {
        R<Boolean> result = remoteUserService.validatePassword(username, rawPassword);
        return result != null && result.isSuccess() && Boolean.TRUE.equals(result.getData());
    }
}
