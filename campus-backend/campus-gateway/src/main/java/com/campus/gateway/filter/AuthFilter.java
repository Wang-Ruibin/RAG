package com.campus.gateway.filter;

import cn.dev33.satoken.exception.SaTokenException;
import cn.dev33.satoken.reactor.filter.SaReactorFilter;
import cn.dev33.satoken.router.SaRouter;
import cn.dev33.satoken.stp.StpUtil;
import cn.dev33.satoken.util.SaResult;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Gateway Sa-Token 鉴权过滤器
 */
@Configuration
public class AuthFilter {

    @Bean
    public SaReactorFilter getSaReactorFilter() {
        return new SaReactorFilter()
                .addInclude("/**")
                .addExclude("/favicon.ico", "/auth/login", "/auth/guest-login", "/auth/logout",
                        "/auth/captcha", "/auth/register",
                        "/v3/api-docs/**", "/doc.html", "/webjars/**", "/error")
                .setAuth(obj -> {
                    // Feign 内部端点与 Python 自带认证：禁止从网关外部访问
                    // （这些端点在服务进程内为 Feign 直连而免登录，网关层原本仅 checkLogin 兜底；
                    //   访客 token 会把它们事实匿名化，如 /system/user/validate 是在线密码爆破入口）
                    SaRouter.match("/system/user/info/**", "/system/user/perms/**", "/system/user/roles/**",
                                    "/system/user/validate/**", "/system/user/register", "/qa/auth/**")
                            .check(r -> {
                                throw new SaTokenException("该接口不允许外部访问");
                            });
                    SaRouter.match("/**")
                            .notMatch("/auth/**")
                            .check(r -> StpUtil.checkLogin());
                })
                .setError(e -> SaResult.error(e.getMessage()).setCode(401));
    }
}
