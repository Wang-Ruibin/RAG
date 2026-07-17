package com.campus.common.security.config;

import cn.dev33.satoken.interceptor.SaInterceptor;
import cn.dev33.satoken.stp.StpUtil;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.boot.autoconfigure.condition.ConditionalOnWebApplication;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * Sa-Token 注解拦截器配置 — 仅在 Servlet Web 应用中生效
 * <p>
 * Gateway（Reactive）不会加载此配置，避免冲突。
 * 注册后 @SaCheckPermission / @SaCheckRole 注解才能正常校验。
 * <p>
 * 排除路径说明：
 * - /auth/login, /auth/logout: Auth 模块公开端点
 * - /auth/captcha, /auth/register: 验证码和注册，无需登录
 * - /system/user/info/**, /perms/**, /roles/**, /validate/**, /register/**: Auth→System Feign 内部调用，必须排除
 *
 * @author CampusQA Team
 */
@AutoConfiguration
@ConditionalOnWebApplication(type = ConditionalOnWebApplication.Type.SERVLET)
@ConditionalOnClass({SaInterceptor.class, WebMvcConfigurer.class})
public class SaTokenWebMvcConfig implements WebMvcConfigurer {

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new SaInterceptor(handle -> StpUtil.checkLogin()))
                .addPathPatterns("/**")
                .excludePathPatterns(
                        "/auth/login",
                        "/auth/logout",
                        "/auth/captcha",
                        "/auth/register",
                        "/system/user/info/**",
                        "/system/user/perms/**",
                        "/system/user/roles/**",
                        "/system/user/validate/**",
                        "/system/user/register/**",
                        "/error",
                        "/favicon.ico"
                );
    }
}
