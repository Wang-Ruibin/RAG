package com.campus.gateway.filter;

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
                .addExclude("/favicon.ico", "/auth/login", "/auth/logout",
                        "/auth/captcha", "/auth/register",
                        "/v3/api-docs/**", "/doc.html", "/webjars/**", "/error")
                .setAuth(obj -> {
                    SaRouter.match("/**")
                            .notMatch("/auth/**")
                            .check(r -> StpUtil.checkLogin());
                })
                .setError(e -> SaResult.error(e.getMessage()).setCode(401));
    }
}
