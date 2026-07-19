package com.campus.gateway.filter;

import cn.dev33.satoken.stp.StpUtil;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.Collections;
import java.util.List;

/**
 * Python 信任头注入 —— 从 JWT 解析登录名，注入 X-Login-Name 传给 Python。
 */
@Component
public class PythonTrustHeaderFilter implements GlobalFilter, Ordered {

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String path = exchange.getRequest().getURI().getPath();

        if (!path.startsWith("/qa/") && !path.startsWith("/qa")
                && !path.startsWith("/knowledge/") && !path.startsWith("/knowledge")) {
            return chain.filter(exchange);
        }

        List<String> authHeaders = exchange.getRequest().getHeaders().get("Authorization");
        if (authHeaders == null || authHeaders.isEmpty()) {
            return chain.filter(exchange);
        }

        String auth = authHeaders.get(0);
        if (auth == null || !auth.startsWith("Bearer ")) {
            return chain.filter(exchange);
        }

        String token = auth.substring(7).trim();
        if (token.isEmpty()) {
            return chain.filter(exchange);
        }

        try {
            Object loginId = StpUtil.getLoginIdByToken(token);
            if (loginId == null) return chain.filter(exchange);

            // 从 Sa-Token Session（Redis）直接读角色和权限，不依赖 StpInterface
            String roleHeader = "";
            String permHeader = "";
            try {
                List<String> roles = StpUtil.getSessionByLoginId(loginId)
                        .get("roles", () -> Collections.emptyList());
                roleHeader = String.join(",", roles);
                List<String> perms = StpUtil.getSessionByLoginId(loginId)
                        .get("permissions", () -> Collections.emptyList());
                permHeader = String.join(",", perms);
            } catch (Exception ignored) {
                // Session 不可用时透传空
            }

            ServerHttpRequest modified = exchange.getRequest().mutate()
                    .header("X-Login-Name", String.valueOf(loginId))
                    .header("X-Login-Roles", roleHeader)
                    .header("X-Login-Perms", permHeader)
                    .build();

            return chain.filter(exchange.mutate().request(modified).build());
        } catch (Exception e) {
            return chain.filter(exchange);
        }
    }

    @Override
    public int getOrder() {
        return 0;
    }
}
