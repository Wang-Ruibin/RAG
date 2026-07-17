package com.campus.common.security.handler;

import cn.dev33.satoken.exception.NotLoginException;
import cn.dev33.satoken.exception.NotPermissionException;
import cn.dev33.satoken.exception.NotRoleException;
import com.campus.common.core.domain.R;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/**
 * Sa-Token 权限异常全局处理
 *
 * @author CampusQA Team
 */
@RestControllerAdvice
@Order(Ordered.HIGHEST_PRECEDENCE)
public class SaTokenExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(SaTokenExceptionHandler.class);

    @ExceptionHandler(NotLoginException.class)
    public R<Void> handleNotLogin(NotLoginException e) {
        log.warn("Token校验失败: {}", e.getMessage());
        return R.unauthorized("登录已过期，请重新登录");
    }

    @ExceptionHandler(NotPermissionException.class)
    public R<Void> handleNotPermission(NotPermissionException e) {
        log.warn("权限不足: {}", e.getMessage());
        return R.forbidden("权限不足，请联系管理员");
    }

    @ExceptionHandler(NotRoleException.class)
    public R<Void> handleNotRole(NotRoleException e) {
        log.warn("角色不匹配: {}", e.getMessage());
        return R.forbidden("角色权限不足");
    }
}
